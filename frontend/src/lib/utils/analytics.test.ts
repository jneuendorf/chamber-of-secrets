import { describe, expect, test } from 'bun:test'

import type { Category, SpendingByCategory, TimeseriesPoint } from '$lib/api/client'
import {
    aggregateTimeseriesToParents,
    aggregateToParents,
    buildCategoryMaps,
    getItemSlices,
    getSpendingSlices,
    toParentLabel,
    UNCATEGORIZED,
} from './analytics'

function makeCat(
    overrides: Partial<Category> & { id: number; name: string },
): Category {
    return {
        parent_id: null,
        icon: null,
        restock_target: null,
        restock_min: null,
        restock_inherit: true,
        ...overrides,
    }
}

const identity = (name: string) => name

const food = makeCat({ id: 1, name: 'Food' })
const dairy = makeCat({ id: 2, name: 'Dairy', parent_id: 1 })
const bakery = makeCat({ id: 3, name: 'Bakery', parent_id: 1 })
const drinks = makeCat({ id: 4, name: 'Drinks' })
const allCats = [food, dairy, bakery, drinks]
const { byName, byId } = buildCategoryMaps(allCats)

describe('toParentLabel', () => {
    test('returns Uncategorized unchanged', () => {
        expect(toParentLabel(UNCATEGORIZED, byName, byId)).toBe(UNCATEGORIZED)
    })

    test('returns own name for root categories', () => {
        expect(toParentLabel('Food', byName, byId)).toBe('Food')
        expect(toParentLabel('Drinks', byName, byId)).toBe('Drinks')
    })

    test('returns parent name for child categories', () => {
        expect(toParentLabel('Dairy', byName, byId)).toBe('Food')
        expect(toParentLabel('Bakery', byName, byId)).toBe('Food')
    })

    test('returns child name if parent_id points to missing category', () => {
        const orphan = makeCat({ id: 10, name: 'Orphan', parent_id: 999 })
        const maps = buildCategoryMaps([orphan])
        expect(toParentLabel('Orphan', maps.byName, maps.byId)).toBe('Orphan')
    })

    test('returns name as-is for unknown categories', () => {
        expect(toParentLabel('Unknown', byName, byId)).toBe('Unknown')
    })
})

describe('aggregateToParents', () => {
    test('aggregates children under parent', () => {
        const rows: SpendingByCategory[] = [
            { category: 'Dairy', total_spent: 10, item_count: 3 },
            { category: 'Bakery', total_spent: 5, item_count: 2 },
            { category: 'Food', total_spent: 8, item_count: 1 },
        ]
        const result = aggregateToParents(rows, byName, byId)
        expect(result).toHaveLength(1)
        expect(result[0].category).toBe('Food')
        expect(result[0].total_spent).toBe(23)
        expect(result[0].item_count).toBe(6)
    })

    test('keeps root categories separate', () => {
        const rows: SpendingByCategory[] = [
            { category: 'Food', total_spent: 10, item_count: 1 },
            { category: 'Drinks', total_spent: 5, item_count: 2 },
        ]
        const result = aggregateToParents(rows, byName, byId)
        expect(result).toHaveLength(2)
        expect(result[0].category).toBe('Food')
        expect(result[1].category).toBe('Drinks')
    })

    test('keeps Uncategorized separate', () => {
        const rows: SpendingByCategory[] = [
            { category: 'Dairy', total_spent: 10, item_count: 1 },
            { category: UNCATEGORIZED, total_spent: 3, item_count: 1 },
        ]
        const result = aggregateToParents(rows, byName, byId)
        expect(result).toHaveLength(2)
        const uncat = result.find((r) => r.category === UNCATEGORIZED)
        expect(uncat?.total_spent).toBe(3)
    })

    test('sorts by total_spent descending', () => {
        const rows: SpendingByCategory[] = [
            { category: 'Drinks', total_spent: 5, item_count: 1 },
            { category: 'Dairy', total_spent: 20, item_count: 3 },
        ]
        const result = aggregateToParents(rows, byName, byId)
        expect(result[0].category).toBe('Food')
        expect(result[1].category).toBe('Drinks')
    })

    test('returns empty for empty input', () => {
        expect(aggregateToParents([], byName, byId)).toEqual([])
    })
})

describe('aggregateTimeseriesToParents', () => {
    test('merges children into parent per date', () => {
        const rows: TimeseriesPoint[] = [
            { date: '2025-01-01', category: 'Dairy', item_count: 2, total_spent: 5 },
            { date: '2025-01-01', category: 'Bakery', item_count: 1, total_spent: 3 },
            { date: '2025-01-02', category: 'Dairy', item_count: 1, total_spent: 2 },
        ]
        const result = aggregateTimeseriesToParents(rows, byName, byId)
        expect(result).toHaveLength(2)
        const day1 = result.find((r) => r.date === '2025-01-01')
        expect(day1?.category).toBe('Food')
        expect(day1?.item_count).toBe(3)
        expect(day1?.total_spent).toBe(8)
    })

    test('sorts by date then category', () => {
        const rows: TimeseriesPoint[] = [
            { date: '2025-01-02', category: 'Drinks', item_count: 1, total_spent: 1 },
            { date: '2025-01-01', category: 'Food', item_count: 1, total_spent: 1 },
            { date: '2025-01-01', category: 'Drinks', item_count: 1, total_spent: 1 },
        ]
        const result = aggregateTimeseriesToParents(rows, byName, byId)
        expect(result[0]).toMatchObject({ date: '2025-01-01', category: 'Drinks' })
        expect(result[1]).toMatchObject({ date: '2025-01-01', category: 'Food' })
        expect(result[2]).toMatchObject({ date: '2025-01-02', category: 'Drinks' })
    })
})

describe('getItemSlices', () => {
    const spending: SpendingByCategory[] = [
        { category: 'Dairy', total_spent: 10, item_count: 3 },
        { category: 'Bakery', total_spent: 5, item_count: 2 },
        { category: 'Drinks', total_spent: 4, item_count: 4 },
        { category: 'Food', total_spent: 8, item_count: 1 },
    ]
    const parentAgg = aggregateToParents(spending, byName, byId)

    test('top-level returns parent aggregations', () => {
        const slices = getItemSlices(null, spending, parentAgg, byName, byId, identity)
        expect(slices).toHaveLength(2)
        const foodSlice = slices.find((s) => s.key === 'Food')
        expect(foodSlice?.value).toBe(6)
    })

    test('parent with multiple children is drillable', () => {
        const slices = getItemSlices(null, spending, parentAgg, byName, byId, identity)
        const foodSlice = slices.find((s) => s.key === 'Food')
        expect(foodSlice?.drillable).toBe(true)
    })

    test('parent with single source row is not drillable', () => {
        const singleChild: SpendingByCategory[] = [
            { category: 'Drinks', total_spent: 4, item_count: 4 },
        ]
        const agg = aggregateToParents(singleChild, byName, byId)
        const slices = getItemSlices(null, singleChild, agg, byName, byId, identity)
        const drinksSlice = slices.find((s) => s.key === 'Drinks')
        expect(drinksSlice?.drillable).toBe(false)
    })

    test('drill-down returns child rows', () => {
        const slices = getItemSlices(
            'Food',
            spending,
            parentAgg,
            byName,
            byId,
            identity,
        )
        expect(slices).toHaveLength(3)
        const labels = slices.map((s) => s.key)
        expect(labels).toContain('Dairy')
        expect(labels).toContain('Bakery')
        expect(labels).toContain('Food')
    })

    test('drill-down slices are never drillable', () => {
        const slices = getItemSlices(
            'Food',
            spending,
            parentAgg,
            byName,
            byId,
            identity,
        )
        expect(slices.every((s) => !s.drillable)).toBe(true)
    })

    test('applies displayCategory to labels', () => {
        const translator = (name: string) =>
            name === UNCATEGORIZED ? 'Translated' : name
        const rows: SpendingByCategory[] = [
            { category: UNCATEGORIZED, total_spent: 0, item_count: 2 },
        ]
        const agg = aggregateToParents(rows, byName, byId)
        const slices = getItemSlices(null, rows, agg, byName, byId, translator)
        expect(slices[0].label).toBe('Translated')
        expect(slices[0].key).toBe(UNCATEGORIZED)
    })
})

describe('getSpendingSlices', () => {
    const spending: SpendingByCategory[] = [
        { category: 'Dairy', total_spent: 10, item_count: 3 },
        { category: 'Bakery', total_spent: 5, item_count: 2 },
        { category: 'Drinks', total_spent: 0, item_count: 4 },
        { category: 'Food', total_spent: 0, item_count: 1 },
    ]
    const parentAgg = aggregateToParents(spending, byName, byId)
    const parentWithPrice = parentAgg.filter((a) => a.total_spent > 0)

    test('top-level excludes parents with zero spending', () => {
        const slices = getSpendingSlices(
            null,
            spending,
            parentWithPrice,
            byName,
            byId,
            identity,
        )
        expect(slices).toHaveLength(1)
        expect(slices[0].key).toBe('Food')
    })

    test('drill-down excludes child rows with zero spending', () => {
        const slices = getSpendingSlices(
            'Food',
            spending,
            parentWithPrice,
            byName,
            byId,
            identity,
        )
        expect(slices).toHaveLength(2)
        const keys = slices.map((s) => s.key)
        expect(keys).toContain('Dairy')
        expect(keys).toContain('Bakery')
        expect(keys).not.toContain('Food')
    })

    test('drillable when multiple children have spending', () => {
        const slices = getSpendingSlices(
            null,
            spending,
            parentWithPrice,
            byName,
            byId,
            identity,
        )
        expect(slices[0].drillable).toBe(true)
    })

    test('not drillable when only one child has spending', () => {
        const rows: SpendingByCategory[] = [
            { category: 'Dairy', total_spent: 10, item_count: 1 },
            { category: 'Bakery', total_spent: 0, item_count: 2 },
        ]
        const agg = aggregateToParents(rows, byName, byId)
        const withPrice = agg.filter((a) => a.total_spent > 0)
        const slices = getSpendingSlices(null, rows, withPrice, byName, byId, identity)
        expect(slices[0].drillable).toBe(false)
    })

    test('drill-down slices are never drillable', () => {
        const slices = getSpendingSlices(
            'Food',
            spending,
            parentWithPrice,
            byName,
            byId,
            identity,
        )
        expect(slices.every((s) => !s.drillable)).toBe(true)
    })
})
