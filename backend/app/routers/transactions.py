from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import InventoryTransaction, Product, Profile
from app.schemas import TransactionCreate, TransactionRead, TransactionUpdate

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("/", response_model=list[TransactionRead])
def list_transactions(
    product_id: int | None = Query(None),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
) -> list[InventoryTransaction]:
    query = db.query(InventoryTransaction).order_by(InventoryTransaction.transacted_at.desc())
    if product_id is not None:
        query = query.filter(InventoryTransaction.product_id == product_id)
    return query.limit(limit).all()


@router.post("/", response_model=TransactionRead, status_code=201)
def create_transaction(
    data: TransactionCreate,
    db: Session = Depends(get_db),
) -> InventoryTransaction:
    product = (
        db.query(Product)
        .options(joinedload(Product.transactions))
        .filter(Product.id == data.product_id)
        .one_or_none()
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # SQLite doesn't enforce the FK (pragma off), so attribution is checked here.
    # Existence only — an archived profile is still a valid target, since a device
    # may hold a stale selection until its next reload.
    if data.profile_id is not None and not db.get(Profile, data.profile_id):
        raise HTTPException(status_code=404, detail="Profile not found")

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
    return transaction


def _get_transaction_or_404(transaction_id: int, db: Session) -> InventoryTransaction:
    transaction = db.get(InventoryTransaction, transaction_id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return transaction


@router.patch("/{transaction_id}", response_model=TransactionRead)
def update_transaction(
    transaction_id: int,
    data: TransactionUpdate,
    db: Session = Depends(get_db),
) -> InventoryTransaction:
    # Mistake-recovery edit. Stock is derived from transactions at query time,
    # so no separate recompute is needed. No stock guard — this is a correction
    # tool and may legitimately fix an over-recorded movement.
    transaction = _get_transaction_or_404(transaction_id, db)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(transaction, key, value)
    db.commit()
    db.refresh(transaction)
    return transaction


@router.delete("/{transaction_id}", status_code=204)
def delete_transaction(transaction_id: int, db: Session = Depends(get_db)) -> None:
    # Powers "undo last movement". Stock recomputes automatically.
    transaction = _get_transaction_or_404(transaction_id, db)
    db.delete(transaction)
    db.commit()
