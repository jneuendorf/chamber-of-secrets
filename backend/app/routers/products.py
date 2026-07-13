import uuid
from pathlib import PurePosixPath

from fastapi import APIRouter, Depends, HTTPException, Path, UploadFile
from sqlalchemy import delete, update
from sqlalchemy.orm import Session, joinedload

from app.config import PRODUCT_IMAGE_DIR, settings
from app.database import get_db
from app.models import InventoryTransaction, Product, ProductRevision
from app.schemas import (
    CategoryRead,
    EANLookupResult,
    ProductCreate,
    ProductMerge,
    ProductRead,
    ProductRevisionRead,
    ProductUpdate,
    ProductWithStock,
)
from app.services.ean_lookup import lookup_ean
from app.services.off_contribute import contribute_image, contribute_product

ALLOWED_IMAGE_TYPES: dict[str, str] = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
}
MAGIC_BYTES: dict[str, list[bytes]] = {
    "jpg": [b"\xff\xd8\xff"],
    "png": [b"\x89PNG\r\n\x1a\n"],
    "webp": [b"RIFF"],  # full signature is RIFF....WEBP, checked below
    "gif": [b"GIF87a", b"GIF89a"],
}
MAX_IMAGE_BYTES = 5 * 1024 * 1024
EXT_TO_CONTENT_TYPE: dict[str, str] = {ext: ct for ct, ext in ALLOWED_IMAGE_TYPES.items()}


def _detect_ext(data: bytes) -> str | None:
    for ext, signatures in MAGIC_BYTES.items():
        for sig in signatures:
            if data[: len(sig)] == sig:
                if ext == "webp" and data[8:12] != b"WEBP":
                    continue
                return ext
    return None


router = APIRouter(prefix="/products", tags=["products"])


def _serialize(product: Product) -> ProductWithStock:

    def _stock(product: Product) -> float:
        return sum(t.quantity if t.type == "in" else -t.quantity for t in product.transactions)

    return ProductWithStock(
        **ProductRead.model_validate(product, from_attributes=True).model_dump(),
        stock=_stock(product),
        category=CategoryRead.model_validate(product.category, from_attributes=True)
        if product.category
        else None,
    )


def _get_or_404(product_id: int, db: Session) -> Product:
    product = (
        db.query(Product)
        .options(joinedload(Product.transactions), joinedload(Product.category))
        .filter(Product.id == product_id)
        .one_or_none()
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.get("/", response_model=list[ProductWithStock])
def list_products(db: Session = Depends(get_db)) -> list[ProductWithStock]:
    products = (
        db.query(Product)
        .options(joinedload(Product.transactions), joinedload(Product.category))
        .all()
    )
    return [_serialize(p) for p in products]


@router.get("/{product_id}", response_model=ProductWithStock)
def get_product(product_id: int, db: Session = Depends(get_db)) -> ProductWithStock:
    product = _get_or_404(product_id, db)
    return _serialize(product)


@router.post("/", response_model=ProductRead, status_code=201)
def create_product(data: ProductCreate, db: Session = Depends(get_db)) -> Product:
    product = Product(**data.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.post("/merge", response_model=ProductWithStock)
def merge_products(data: ProductMerge, db: Session = Depends(get_db)) -> ProductWithStock:
    """Merge duplicates: move the source's transactions onto the target, then
    delete the source (and its revisions/image). Stock is recomputed."""
    source = db.get(Product, data.source_id)
    target = db.get(Product, data.target_id)
    if not source or not target:
        raise HTTPException(status_code=404, detail="Product not found")

    db.execute(
        update(InventoryTransaction)
        .where(InventoryTransaction.product_id == source.id)
        .values(product_id=target.id),
    )
    _remove_old_upload(source.image_url)
    db.execute(delete(ProductRevision).where(ProductRevision.product_id == source.id))
    db.execute(delete(Product).where(Product.id == source.id))
    db.commit()
    return _serialize(_get_or_404(target.id, db))


@router.delete("/{product_id}", status_code=204)
def delete_product(product_id: int, db: Session = Depends(get_db)) -> None:
    """Delete a product and cascade its transactions, revisions, and local image."""
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    _remove_old_upload(product.image_url)
    db.execute(delete(InventoryTransaction).where(InventoryTransaction.product_id == product_id))
    db.execute(delete(ProductRevision).where(ProductRevision.product_id == product_id))
    db.execute(delete(Product).where(Product.id == product_id))
    db.commit()


@router.patch("/{product_id}", response_model=ProductRead)
def update_product(
    product_id: int,
    data: ProductUpdate,
    db: Session = Depends(get_db),
) -> Product:
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(product, key, value)
    db.commit()
    db.refresh(product)
    return product


def _remove_old_upload(image_url: str | None) -> None:
    # Only delete local uploads; external URLs (e.g. Open Food Facts) have no local file.
    if image_url and image_url.startswith("/api/uploads/products/"):
        old = PRODUCT_IMAGE_DIR / image_url.split("/")[-1]
        old.unlink(missing_ok=True)


def _read_local_upload(image_url: str | None) -> tuple[bytes, str, str] | None:
    """Return (bytes, filename, content_type) for a locally-stored product image,
    or None if there is no usable local file. Powers the OFF image contribution;
    external image URLs have no local bytes to send."""
    if not image_url or not image_url.startswith("/api/uploads/products/"):
        return None

    path = PRODUCT_IMAGE_DIR / PurePosixPath(image_url).name
    if not path.is_file():
        return None

    content_type = EXT_TO_CONTENT_TYPE.get(path.suffix.lstrip(".").lower())
    if not content_type:
        return None

    return path.read_bytes(), path.name, content_type


@router.post("/{product_id}/image", response_model=ProductRead)
async def upload_product_image(
    product_id: int,
    file: UploadFile,
    db: Session = Depends(get_db),
) -> Product:
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    contents = await file.read()
    if len(contents) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image must be smaller than 5 MB")

    ext = _detect_ext(contents)
    if not ext:
        allowed = ", ".join(v.upper() for v in ALLOWED_IMAGE_TYPES.values())
        raise HTTPException(status_code=422, detail=f"File must be {allowed}")

    filename = f"{product_id}_{uuid.uuid4().hex[:8]}.{ext}"
    (PRODUCT_IMAGE_DIR / filename).write_bytes(contents)

    _remove_old_upload(product.image_url)
    product.image_url = f"/api/uploads/products/{filename}"
    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}/image", status_code=204)
def delete_product_image(
    product_id: int,
    db: Session = Depends(get_db),
) -> None:
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    _remove_old_upload(product.image_url)
    product.image_url = None
    db.commit()


@router.get("/lookup/{ean}")
async def lookup_product_by_ean(
    ean: str = Path(openapi_examples={"haribo": {"summary": "Nutella", "value": "4008400404127"}}),
    db: Session = Depends(get_db),
) -> EANLookupResult:
    # Cache hit: product already in the local catalog
    cached = db.query(Product).filter(Product.ean == ean).one_or_none()
    if cached:
        return EANLookupResult(
            ean=ean,
            name=cached.name,
            brand=cached.brand,
            image_url=cached.image_url,
            category=cached.category.name if cached.category else None,
            from_cache=True,
        )

    # Cache miss: fetch from Open Food Facts
    result = await lookup_ean(ean)
    if not result:
        raise HTTPException(status_code=404, detail="Product not found in EAN database")
    return result


@router.post("/{product_id}/contribute")
async def contribute_product_to_off(
    product_id: int,
    db: Session = Depends(get_db),
) -> dict[str, bool]:
    """Opt-in: submit a manually-created product back to Open Food Facts (WL-4.6).

    Barcode-only — OFF is EAN-keyed, so non-EAN products cannot be shared.
    """
    product = _get_or_404(product_id, db)
    if not product.ean:
        raise HTTPException(status_code=400, detail="Product has no barcode — cannot contribute")

    ok = await contribute_product(
        code=product.ean,
        name=product.name,
        brand=product.brand,
        category=product.category.name if product.category else None,
    )
    if not ok:
        raise HTTPException(status_code=502, detail="Open Food Facts rejected the submission")

    # Front-image upload: dormant until off_contribute_images is enabled. Best
    # effort — the text fields are already saved, so a failed image is non-fatal.
    if settings.off_contribute_images:
        image = _read_local_upload(product.image_url)
        if image:
            image_bytes, filename, content_type = image
            await contribute_image(product.ean, image_bytes, filename, content_type)

    return {"ok": True}


@router.post("/{product_id}/refresh", response_model=ProductRead)
async def refresh_product(product_id: int, db: Session = Depends(get_db)) -> Product:
    """Re-fetch product data from the EAN API. Snapshots current data to revision history first."""
    product = _get_or_404(product_id, db)

    if not product.ean:
        raise HTTPException(status_code=400, detail="Product has no EAN — cannot refresh")

    # Snapshot current state before overwriting
    db.add(
        ProductRevision(
            product_id=product.id,
            name=product.name,
            brand=product.brand,
            image_url=product.image_url,
        ),
    )

    fresh = await lookup_ean(product.ean)
    if not fresh:
        raise HTTPException(status_code=502, detail="EAN API returned no data for this product")

    product.name = fresh.name or product.name
    product.brand = fresh.brand
    product.image_url = fresh.image_url

    db.commit()
    db.refresh(product)
    return product


@router.get("/{product_id}/revisions", response_model=list[ProductRevisionRead])
def list_revisions(product_id: int, db: Session = Depends(get_db)) -> list[ProductRevision]:
    """Return the revision history for a product, newest first."""
    if not db.get(Product, product_id):
        raise HTTPException(status_code=404, detail="Product not found")
    revisions = (
        db.query(ProductRevision)
        .filter(ProductRevision.product_id == product_id)
        .order_by(ProductRevision.superseded_at.desc())
        .all()
    )
    return revisions
