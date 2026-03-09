from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

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
    if not db.get(Product, data.product_id):
        raise HTTPException(status_code=404, detail="Product not found")

    transaction = InventoryTransaction(**data.model_dump())
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction  # type: ignore[return-value]
