import uuid

from fastapi import APIRouter, Depends, HTTPException, Path, UploadFile
from sqlalchemy.orm import Session, joinedload

from app.config import PRODUCT_IMAGE_DIR
from app.database import get_db
from app.models import Product, ProductRevision
from app.schemas import (
    CategoryRead,
    EANLookupResult,
    ProductCreate,
    ProductRead,
    ProductRevisionRead,
    ProductUpdate,
    ProductWithStock,
)
from app.services.ean_lookup import lookup_ean

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
def create_product(data: ProductCreate, db: Session = Depends(get_db)) -> ProductRead:
    product = Product(**data.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product  # type: ignore[return-value]


@router.patch("/{product_id}", response_model=ProductRead)
def update_product(
    product_id: int,
    data: ProductUpdate,
    db: Session = Depends(get_db),
) -> ProductRead:
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(product, key, value)
    db.commit()
    db.refresh(product)
    return ProductRead.model_validate(product, from_attributes=True)


def _remove_old_upload(image_url: str | None) -> None:
    # Only delete local uploads; external URLs (e.g. Open Food Facts) have no local file.
    if image_url and image_url.startswith("/api/uploads/products/"):
        old = PRODUCT_IMAGE_DIR / image_url.split("/")[-1]
        old.unlink(missing_ok=True)


@router.post("/{product_id}/image", response_model=ProductRead)
async def upload_product_image(
    product_id: int,
    file: UploadFile,
    db: Session = Depends(get_db),
) -> ProductRead:
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
    return ProductRead.model_validate(product, from_attributes=True)


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


@router.post("/{product_id}/refresh", response_model=ProductRead)
async def refresh_product(product_id: int, db: Session = Depends(get_db)) -> ProductRead:
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
    return product  # type: ignore[return-value]


@router.get("/{product_id}/revisions", response_model=list[ProductRevisionRead])
def list_revisions(product_id: int, db: Session = Depends(get_db)) -> list[ProductRevisionRead]:
    """Return the revision history for a product, newest first."""
    if not db.get(Product, product_id):
        raise HTTPException(status_code=404, detail="Product not found")
    revisions = (
        db.query(ProductRevision)
        .filter(ProductRevision.product_id == product_id)
        .order_by(ProductRevision.superseded_at.desc())
        .all()
    )
    return revisions  # type: ignore[return-value]
