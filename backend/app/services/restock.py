from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models import Category, Product


UNCATEGORIZED_LABEL = "Uncategorized"


@dataclass(slots=True)
class ResolvedPolicy:
    effective_target: float | None
    effective_min: float | None
    resolved_target_from_category_id: int | None
    resolved_min_from_category_id: int | None
    resolved_from_category_id: int | None


@dataclass(slots=True)
class RestockComputed:
    missing_to_target: float
    below_min: bool
    needs_restock: bool


@dataclass(slots=True)
class RestockOverviewRowData:
    id: int
    name: str
    brand: str | None
    category_id: int | None
    category_name: str
    current_stock: float
    effective_target: float | None
    effective_min: float | None
    resolved_from_category_id: int | None
    missing_to_target: float
    below_min: bool
    needs_restock: bool
    top_parent_category_id: int | None
    top_parent_category_name: str


@dataclass(slots=True)
class RestockGroupTotalData:
    category_id: int | None
    category_name: str
    total_missing_to_target: float
    affected_products: int


def compute_stock_for_product(product: Product) -> float:
    return sum(tx.quantity if tx.type == "in" else -tx.quantity for tx in product.transactions)


def resolve_restock_policy(
    category: Category | None,
    category_by_id: dict[int, Category],
) -> ResolvedPolicy:
    if category is None:
        return ResolvedPolicy(
            effective_target=None,
            effective_min=None,
            resolved_target_from_category_id=None,
            resolved_min_from_category_id=None,
            resolved_from_category_id=None,
        )

    effective_target, target_from = _resolve_single_field(
        category=category,
        category_by_id=category_by_id,
        field_name="restock_target",
    )
    effective_min, min_from = _resolve_single_field(
        category=category,
        category_by_id=category_by_id,
        field_name="restock_min",
    )

    resolved_from: int | None = None
    if target_from is not None and min_from is not None:
        resolved_from = target_from if target_from == min_from else category.id
    elif target_from is not None:
        resolved_from = target_from
    elif min_from is not None:
        resolved_from = min_from

    return ResolvedPolicy(
        effective_target=effective_target,
        effective_min=effective_min,
        resolved_target_from_category_id=target_from,
        resolved_min_from_category_id=min_from,
        resolved_from_category_id=resolved_from,
    )


def compute_restock(
    current_stock: float,
    effective_target: float | None,
    effective_min: float | None,
) -> RestockComputed:
    missing_to_target = (
        max(effective_target - current_stock, 0.0) if effective_target is not None else 0.0
    )
    below_min = effective_min is not None and current_stock < effective_min
    needs_restock = missing_to_target > 0 or below_min
    return RestockComputed(
        missing_to_target=missing_to_target,
        below_min=below_min,
        needs_restock=needs_restock,
    )


def top_parent_category(
    category: Category | None,
    category_by_id: dict[int, Category],
) -> Category | None:
    if category is None:
        return None

    visited: set[int] = set()
    current = category
    while current.parent_id is not None:
        if current.id in visited:
            return current
        visited.add(current.id)

        parent = category_by_id.get(current.parent_id)
        if parent is None:
            return current
        current = parent

    return current


def build_restock_overview_rows(
    products: list[Product],
    category_by_id: dict[int, Category],
    *,
    include_all_products: bool = True,
) -> list[RestockOverviewRowData]:
    rows: list[RestockOverviewRowData] = []

    for product in products:
        category = (
            category_by_id.get(product.category_id) if product.category_id is not None else None
        )
        category_name = category.name if category is not None else UNCATEGORIZED_LABEL

        policy = resolve_restock_policy(category, category_by_id)
        current_stock = compute_stock_for_product(product)
        computed = compute_restock(
            current_stock=current_stock,
            effective_target=policy.effective_target,
            effective_min=policy.effective_min,
        )

        if not include_all_products and not computed.needs_restock:
            continue

        top_parent = top_parent_category(category, category_by_id)
        top_parent_id = top_parent.id if top_parent is not None else None
        top_parent_name = top_parent.name if top_parent is not None else UNCATEGORIZED_LABEL

        rows.append(
            RestockOverviewRowData(
                id=product.id,
                name=product.name,
                brand=product.brand,
                category_id=product.category_id,
                category_name=category_name,
                current_stock=current_stock,
                effective_target=policy.effective_target,
                effective_min=policy.effective_min,
                resolved_from_category_id=policy.resolved_from_category_id,
                missing_to_target=computed.missing_to_target,
                below_min=computed.below_min,
                needs_restock=computed.needs_restock,
                top_parent_category_id=top_parent_id,
                top_parent_category_name=top_parent_name,
            )
        )

    return rows


def aggregate_restock_totals(
    rows: list[RestockOverviewRowData],
) -> tuple[list[RestockGroupTotalData], list[RestockGroupTotalData], float, int]:
    child_totals = _aggregate(
        rows=rows,
        key=lambda r: (r.category_id, r.category_name),
    )
    parent_totals = _aggregate(
        rows=rows,
        key=lambda r: (r.top_parent_category_id, r.top_parent_category_name),
    )

    total_missing_quantity = sum(r.missing_to_target for r in rows)
    total_products_needing_restock = sum(1 for r in rows if r.needs_restock)

    return child_totals, parent_totals, total_missing_quantity, total_products_needing_restock


def _resolve_single_field(
    *,
    category: Category,
    category_by_id: dict[int, Category],
    field_name: str,
) -> tuple[float | None, int | None]:
    visited: set[int] = set()
    current: Category | None = category

    while current is not None:
        if current.id in visited:
            return None, None
        visited.add(current.id)

        value = getattr(current, field_name)
        if value is not None:
            return float(value), current.id

        if not current.restock_inherit or current.parent_id is None:
            return None, None

        current = category_by_id.get(current.parent_id)

    return None, None


def _aggregate(
    *,
    rows: list[RestockOverviewRowData],
    key,
) -> list[RestockGroupTotalData]:
    buckets: dict[tuple[int | None, str], RestockGroupTotalData] = {}

    for row in rows:
        bucket_id, bucket_name = key(row)
        bucket_key = (bucket_id, bucket_name)

        bucket = buckets.get(bucket_key)
        if bucket is None:
            bucket = RestockGroupTotalData(
                category_id=bucket_id,
                category_name=bucket_name,
                total_missing_to_target=0.0,
                affected_products=0,
            )
            buckets[bucket_key] = bucket

        bucket.total_missing_to_target += row.missing_to_target
        if row.needs_restock:
            bucket.affected_products += 1

    return sorted(
        buckets.values(),
        key=lambda b: (b.total_missing_to_target, b.affected_products),
        reverse=True,
    )
