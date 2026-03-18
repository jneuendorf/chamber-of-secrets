from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import InventoryTransaction, Product
from app.schemas import TransactionCreate, TransactionRead

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("/", response_model=list[TransactionRead])
def list_transactions(
    product_id: int | None = Query(None),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
) -> list[TransactionRead]:
    query = db.query(InventoryTransaction).order_by(InventoryTransaction.transacted_at.desc())
    if product_id is not None:
        query = query.filter(InventoryTransaction.product_id == product_id)
    return query.limit(limit).all()  # type: ignore[return-value]


@router.post("/", response_model=TransactionRead, status_code=201)
def create_transaction(data: TransactionCreate, db: Session = Depends(get_db)) -> TransactionRead:
    product = (
        db.query(Product)
        .options(joinedload(Product.transactions))
        .filter(Product.id == data.product_id)
        .one_or_none()
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if data.type == "out":
        current_stock = sum(
            t.quantity if t.type == "in" else -t.quantity for t in product.transactions
        )
        if data.quantity > current_stock:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock: available {current_stock}, requested {data.quantity}",
            )

    transaction = InventoryTransaction(**data.model_dump())
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction  # type: ignore[return-value]
