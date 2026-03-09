from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Category, InventoryTransaction, Product
from app.schemas import SpendingByCategory, TimeseriesPoint

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
        .group_by(Category.name)
        .order_by(func.sum(InventoryTransaction.quantity * InventoryTransaction.unit_price).desc())
    )

    if since:
        query = query.where(InventoryTransaction.transacted_at >= since)
    if until:
        query = query.where(InventoryTransaction.transacted_at < until + timedelta(days=1))

    result = db.execute(query)
    return [
        SpendingByCategory(
            category=row.category, total_spent=row.total_spent or 0, item_count=row.item_count
        )
        for row in result.all()
    ]


@router.get("/timeseries", response_model=list[TimeseriesPoint])
def timeseries_by_category(
    since: datetime | None = Query(None, description="Start date (ISO format)"),
    until: datetime | None = Query(None, description="End date (ISO format)"),
    db: Session = Depends(get_db),
) -> list[TimeseriesPoint]:
    query = (
        select(
            func.date(InventoryTransaction.transacted_at).label("date"),
            func.coalesce(Category.name, "Uncategorized").label("category"),
            func.count(InventoryTransaction.id).label("item_count"),
            func.coalesce(
                func.sum(InventoryTransaction.quantity * InventoryTransaction.unit_price), 0
            ).label("total_spent"),
        )
        .select_from(InventoryTransaction)
        .join(Product, InventoryTransaction.product_id == Product.id)
        .outerjoin(Category, Product.category_id == Category.id)
        .where(InventoryTransaction.type == "in")
        .group_by(func.date(InventoryTransaction.transacted_at), Category.name)
        .order_by(func.date(InventoryTransaction.transacted_at).asc())
    )

    if since:
        query = query.where(InventoryTransaction.transacted_at >= since)
    if until:
        query = query.where(InventoryTransaction.transacted_at < until + timedelta(days=1))

    result = db.execute(query)
    return [
        TimeseriesPoint(
            date=row.date,
            category=row.category,
            item_count=row.item_count,
            total_spent=row.total_spent,
        )
        for row in result.all()
    ]
