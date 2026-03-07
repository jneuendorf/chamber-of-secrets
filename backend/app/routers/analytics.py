from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Category, InventoryTransaction, Product
from app.schemas import SpendingByCategory

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/spending", response_model=list[SpendingByCategory])
def spending_by_category(
    since: datetime | None = Query(None, description="Start date (ISO format)"),
    until: datetime | None = Query(None, description="End date (ISO format)"),
    db: Session = Depends(get_db),
) -> list[SpendingByCategory]:
    query = (
        select(
            func.coalesce(Category.name, "Uncategorized").label("category"),
            func.sum(InventoryTransaction.quantity * InventoryTransaction.unit_price).label(
                "total_spent"
            ),
            func.count(InventoryTransaction.id).label("item_count"),
        )
        .select_from(InventoryTransaction)
        .join(Product, InventoryTransaction.product_id == Product.id)
        .outerjoin(Category, Product.category_id == Category.id)
        .where(InventoryTransaction.type == "in")
        .where(InventoryTransaction.unit_price.is_not(None))
        .group_by(Category.name)
        .order_by(func.sum(InventoryTransaction.quantity * InventoryTransaction.unit_price).desc())
    )

    if since:
        query = query.where(InventoryTransaction.transacted_at >= since)
    if until:
        query = query.where(InventoryTransaction.transacted_at <= until)

    result = db.execute(query)
    return [
        SpendingByCategory(
            category=row.category, total_spent=row.total_spent or 0, item_count=row.item_count
        )
        for row in result.all()
    ]
