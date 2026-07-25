from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.schemas import RestockGroupTotal, RestockOverviewResponse, RestockOverviewRow

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


def build_restock_overview(
    products: list[Product],
    category_by_id: dict[int, Category],
    *,
    include_all_products: bool = True,
) -> RestockOverviewResponse:
    rows: list[RestockOverviewRow] = []
    child_buckets: dict[tuple[int | None, str], RestockGroupTotal] = {}
    parent_buckets: dict[tuple[int | None, str], RestockGroupTotal] = {}
    total_missing_quantity = 0.0
    total_products_needing_restock = 0

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
            RestockOverviewRow(
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
            ),
        )

        total_missing_quantity += computed.missing_to_target
        if computed.needs_restock:
            total_products_needing_restock += 1
        _accumulate(child_buckets, (product.category_id, category_name), computed)
        _accumulate(parent_buckets, (top_parent_id, top_parent_name), computed)

    rows.sort(
        key=lambda r: (r.needs_restock, r.below_min, r.missing_to_target, r.name.lower()),
        reverse=True,
    )

    return RestockOverviewResponse(
        rows=rows,
        total_missing_quantity=total_missing_quantity,
        total_products_needing_restock=total_products_needing_restock,
        by_child_category=_sorted_totals(child_buckets),
        by_parent_category=_sorted_totals(parent_buckets),
    )


def _accumulate(
    buckets: dict[tuple[int | None, str], RestockGroupTotal],
    key: tuple[int | None, str],
    computed: RestockComputed,
) -> None:
    bucket = buckets.get(key)
    if bucket is None:
        bucket = RestockGroupTotal(
            category_id=key[0],
            category_name=key[1],
            total_missing_to_target=0.0,
            affected_products=0,
        )
        buckets[key] = bucket

    bucket.total_missing_to_target += computed.missing_to_target
    if computed.needs_restock:
        bucket.affected_products += 1


def _sorted_totals(
    buckets: dict[tuple[int | None, str], RestockGroupTotal],
) -> list[RestockGroupTotal]:
    return sorted(
        buckets.values(),
        key=lambda b: (b.total_missing_to_target, b.affected_products),
        reverse=True,
    )


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
