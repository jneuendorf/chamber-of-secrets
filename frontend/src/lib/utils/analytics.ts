import type { Category, SpendingByCategory, TimeseriesPoint } from '$lib/api/client'

/** Backend sentinel for products without a category. */
export const UNCATEGORIZED = 'Uncategorized'

/** Aggregated spending row rolled up to parent-category level. */
export type Agg = { category: string; total_spent: number; item_count: number }

/** A single segment in the drill-down donut chart. */
export interface Slice {
    label: string
    value: number
    key: string
    drillable: boolean
}

/** Index categories by name and by id for O(1) lookups. */
export function buildCategoryMaps(categories: Category[]): {
    byName: Map<string, Category>
    byId: Map<number, Category>
} {
    return {
        byName: new Map(categories.map((c) => [c.name, c])),
        byId: new Map(categories.map((c) => [c.id, c])),
    }
}

/** Resolve a child category name to its parent's name (or itself for roots). */
export function toParentLabel(
    childName: string,
    byName: Map<string, Category>,
    byId: Map<number, Category>,
): string {
    if (childName === UNCATEGORIZED) {
        return UNCATEGORIZED
    }
    const child = byName.get(childName)
    if (!child) {
        return childName
    }
    if (child.parent_id == null) {
        return child.name
    }
    const parent = byId.get(child.parent_id)
    return parent?.name ?? child.name
}

/** Roll up spending rows to parent categories, sorted by total_spent descending. */
export function aggregateToParents(
    rows: SpendingByCategory[],
    byName: Map<string, Category>,
    byId: Map<number, Category>,
): Agg[] {
    const m = new Map<string, Agg>()
    for (const row of rows) {
        const label = toParentLabel(row.category, byName, byId)
        const prev = m.get(label) ?? {
            category: label,
            total_spent: 0,
            item_count: 0,
        }
        prev.total_spent += row.total_spent
        prev.item_count += row.item_count
        m.set(label, prev)
    }
    return [...m.values()].sort((a, b) => b.total_spent - a.total_spent)
}

/** Roll up timeseries points to parent categories per date, sorted by date then category. */
export function aggregateTimeseriesToParents(
    rows: TimeseriesPoint[],
    byName: Map<string, Category>,
    byId: Map<number, Category>,
): TimeseriesPoint[] {
    const m = new Map<string, TimeseriesPoint>()
    for (const row of rows) {
        const parentCategory = toParentLabel(row.category, byName, byId)
        const key = `${row.date}__${parentCategory}`
        const prev = m.get(key) ?? {
            date: row.date,
            category: parentCategory,
            item_count: 0,
            total_spent: 0,
        }
        prev.item_count += row.item_count
        prev.total_spent += row.total_spent
        m.set(key, prev)
    }
    return [...m.values()].sort((a, b) =>
        a.date === b.date
            ? a.category.localeCompare(b.category)
            : a.date.localeCompare(b.date),
    )
}

/** Build donut slices for item counts. Top-level shows parents; drill-down shows children. */
export function getItemSlices(
    parentKey: string | null,
    spending: SpendingByCategory[],
    parentSpending: Agg[],
    byName: Map<string, Category>,
    byId: Map<number, Category>,
    displayCategory: (name: string) => string,
): Slice[] {
    if (parentKey === null) {
        return parentSpending.map((row) => {
            const childRows = spending.filter(
                (s) => toParentLabel(s.category, byName, byId) === row.category,
            )
            return {
                label: displayCategory(row.category),
                value: row.item_count,
                key: row.category,
                drillable: childRows.length > 1,
            }
        })
    }
    return spending
        .filter((s) => toParentLabel(s.category, byName, byId) === parentKey)
        .map((s) => ({
            label: displayCategory(s.category),
            value: s.item_count,
            key: s.category,
            drillable: false,
        }))
}

/** Build donut slices for spending amounts. Excludes rows with zero spending. */
export function getSpendingSlices(
    parentKey: string | null,
    spending: SpendingByCategory[],
    parentSpendingWithPrice: Agg[],
    byName: Map<string, Category>,
    byId: Map<number, Category>,
    displayCategory: (name: string) => string,
): Slice[] {
    if (parentKey === null) {
        return parentSpendingWithPrice.map((row) => {
            const childRows = spending.filter(
                (s) =>
                    toParentLabel(s.category, byName, byId) === row.category &&
                    s.total_spent > 0,
            )
            return {
                label: displayCategory(row.category),
                value: row.total_spent,
                key: row.category,
                drillable: childRows.length > 1,
            }
        })
    }
    return spending
        .filter(
            (s) =>
                toParentLabel(s.category, byName, byId) === parentKey &&
                s.total_spent > 0,
        )
        .map((s) => ({
            label: displayCategory(s.category),
            value: s.total_spent,
            key: s.category,
            drillable: false,
        }))
}
