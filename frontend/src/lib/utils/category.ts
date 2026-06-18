import type { Category } from '$lib/api/client'

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
