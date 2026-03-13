from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Category, InventoryTransaction, Product
from app.schemas import (
    RestockGroupTotal,
    RestockOverviewResponse,
    RestockOverviewRow,
    SpendingByCategory,
    TimeseriesPoint,
)
from app.services.restock import aggregate_restock_totals, build_restock_overview_rows

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


@router.get("/restock-overview", response_model=RestockOverviewResponse)
def restock_overview(
    include_all_products: bool = Query(
        False,
        description="If true, include products that do not currently need restocking",
    ),
    db: Session = Depends(get_db),
) -> RestockOverviewResponse:
    categories = db.query(Category).all()
    category_by_id = {category.id: category for category in categories}

    products = (
        db.query(Product)
        .options(joinedload(Product.transactions), joinedload(Product.category))
        .all()
    )

    rows_data = build_restock_overview_rows(
        products=products,
        category_by_id=category_by_id,
        include_all_products=include_all_products,
    )

    (
        child_totals_data,
        parent_totals_data,
        total_missing_quantity,
        total_products_needing_restock,
    ) = aggregate_restock_totals(rows_data)

    rows = [
        RestockOverviewRow(
            id=row.id,
            name=row.name,
            brand=row.brand,
            category_id=row.category_id,
            category_name=row.category_name,
            current_stock=row.current_stock,
            effective_target=row.effective_target,
            effective_min=row.effective_min,
            resolved_from_category_id=row.resolved_from_category_id,
            missing_to_target=row.missing_to_target,
            below_min=row.below_min,
            needs_restock=row.needs_restock,
        )
        for row in rows_data
    ]
    rows.sort(
        key=lambda r: (r.needs_restock, r.below_min, r.missing_to_target, r.name.lower()),
        reverse=True,
    )

    by_child_category = [
        RestockGroupTotal(
            category_id=group.category_id,
            category_name=group.category_name,
            total_missing_to_target=group.total_missing_to_target,
            affected_products=group.affected_products,
        )
        for group in child_totals_data
    ]
    by_parent_category = [
        RestockGroupTotal(
            category_id=group.category_id,
            category_name=group.category_name,
            total_missing_to_target=group.total_missing_to_target,
            affected_products=group.affected_products,
        )
        for group in parent_totals_data
    ]

    return RestockOverviewResponse(
        rows=rows,
        total_missing_quantity=total_missing_quantity,
        total_products_needing_restock=total_products_needing_restock,
        by_child_category=by_child_category,
        by_parent_category=by_parent_category,
    )
