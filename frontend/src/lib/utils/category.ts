import type { Category } from '$lib/api/client'

/** Effective restock thresholds resolved through the category inheritance chain. */
export interface RestockPolicy {
    target: number | null
    min: number | null
    targetFrom: number | null
    minFrom: number | null
}

/** Stock health relative to the effective restock policy. */
export type StockStatus = 'out' | 'low' | 'ok'

/**
 * Resolve the effective restock target/min for a category by walking up the
 * parent chain, honouring each level's `restock_inherit` flag. Mirrors the
 * backend `_resolve_single_field` logic so the inventory badge and the restock
 * overview agree on what "low" means.
 */
export function resolveRestockPolicy(
    category: Category | null | undefined,
    allCategories: Category[],
): RestockPolicy {
    if (!category) {
        return { target: null, min: null, targetFrom: null, minFrom: null }
    }

    const byId = new Map(allCategories.map((cat) => [cat.id, cat]))

    const resolveField = (
        field: 'restock_target' | 'restock_min',
    ): [number | null, number | null] => {
        const visited = new Set<number>()
        let cur: Category | undefined = category
        while (cur) {
            if (visited.has(cur.id)) {
                return [null, null]
            }
            visited.add(cur.id)

            const value = cur[field]
            if (value != null) {
                return [value, cur.id]
            }
            if (!cur.restock_inherit || cur.parent_id == null) {
                return [null, null]
            }
            cur = byId.get(cur.parent_id)
        }
        return [null, null]
    }

    const [target, targetFrom] = resolveField('restock_target')
    const [min, minFrom] = resolveField('restock_min')
    return { target, min, targetFrom, minFrom }
}

/**
 * Classify a product's stock against its effective restock policy. `out` when
 * depleted; `low` when it needs restocking (below min or under target),
 * matching the backend `needs_restock` definition; otherwise `ok`.
 */
export function stockStatus(stock: number, policy: RestockPolicy): StockStatus {
    if (stock <= 0) {
        return 'out'
    }
    const missingToTarget =
        policy.target != null ? Math.max(policy.target - stock, 0) : 0
    const belowMin = policy.min != null && stock < policy.min
    return missingToTarget > 0 || belowMin ? 'low' : 'ok'
}

export function resolveIcon(
    category: Category | null | undefined,
    allCategories: Category[],
): string | null {
    if (!category) {
        return null
    }

    const byId = new Map(allCategories.map((c) => [c.id, c]))
    const visited = new Set<number>()
    let cur: Category | undefined = category

    while (cur) {
        if (visited.has(cur.id)) {
            break
        }
        visited.add(cur.id)
        if (cur.icon) {
            return cur.icon
        }
        if (cur.parent_id == null) {
            break
        }
        cur = byId.get(cur.parent_id)
    }

    return null
}
