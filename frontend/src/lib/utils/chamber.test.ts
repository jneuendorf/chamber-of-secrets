import { describe, expect, test } from 'bun:test'

import type { Category, Product } from '$lib/api/client'
import { buildDots, DOT_CAP, emojiFor, visibleSlots } from './chamber'

function makeProduct(
    overrides: Partial<Product> & { id: number; stock: number },
): Product {
    return {
        name: 'Item',
        brand: null,
        category: null,
        category_id: null,
        ean: null,
        image_url: null,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
        ...overrides,
    }
}

function makeCategory(id: number, name: string): Category {
    return {
        id,
        name,
        parent_id: null,
        icon: null,
        restock_target: null,
        restock_min: null,
        restock_inherit: true,
    }
}

describe('visibleSlots', () => {
    test('renders one slot per unit below the cap', () => {
        expect(visibleSlots(0)).toEqual([])
        expect(visibleSlots(3)).toEqual([0, 1, 2])
    })

    test('saturates at the cap for large stock', () => {
        const shown = visibleSlots(DOT_CAP * 10)
        expect(shown).toEqual(Array.from({ length: DOT_CAP }, (_, index) => index))
    })

    // Consuming the *tapped* slot must drop exactly that slot — this is the fix
    // for "a different icon than the one I tapped disappeared".
    test('a consumed low slot is the one removed (small pile keeps its holes)', () => {
        expect(visibleSlots(3, [1])).toEqual([0, 2])
    })

    // A big pile has a reserve beyond the cap, so consuming a visible slot pulls
    // in the next reserve slot instead of leaving a phantom gap.
    test('a big pile refills from the reserve when a slot is consumed', () => {
        const shown = visibleSlots(DOT_CAP * 3, [3])
        expect(shown).toHaveLength(DOT_CAP) // pile stays full
        expect(shown).not.toContain(3) // the consumed slot is gone
        expect(shown).toContain(DOT_CAP) // a reserve slot filled its place
    })

    test('consumed count shrinks a small pile below the cap', () => {
        expect(visibleSlots(3, [0, 1])).toEqual([2])
    })
})

describe('emojiFor', () => {
    test('matches known keywords, falls back to a box', () => {
        expect(emojiFor('Vollmilch 3.5%', 'Dairy')).toBe('🥛')
        expect(emojiFor('Mystery Widget', null)).toBe('📦')
    })
})

describe('buildDots', () => {
    test('a depleted product contributes no dots', () => {
        const dots = buildDots([makeProduct({ id: 1, stock: 0 })], [])
        expect(dots).toHaveLength(0)
    })

    test('stock above the cap saturates the pile', () => {
        const dots = buildDots([makeProduct({ id: 1, stock: 99 })], [])
        expect(dots).toHaveLength(DOT_CAP)
    })

    test('placement is deterministic across builds', () => {
        const products = [makeProduct({ id: 7, stock: 4 })]
        expect(buildDots(products, [])).toEqual(buildDots(products, []))
    })

    // The core WL-5.2 invariant: consuming one unit removes exactly one dot and
    // leaves every surviving dot at the identical key and position. Without it,
    // a single tap would reshuffle the whole pile.
    test('consuming one unit removes exactly one dot, siblings unchanged', () => {
        const before = buildDots([makeProduct({ id: 5, stock: 5 })], [])
        const after = buildDots([makeProduct({ id: 5, stock: 4 })], [])

        expect(before).toHaveLength(5)
        expect(after).toHaveLength(4)

        // The dropped dot is the highest slot; the rest are pointwise identical.
        expect(before.map((dot) => dot.key)).toEqual([
            '5:0',
            '5:1',
            '5:2',
            '5:3',
            '5:4',
        ])
        for (const survivor of after) {
            const original = before.find((dot) => dot.key === survivor.key)
            expect(original).toBeDefined()
            expect(survivor.x).toBe(original!.x)
            expect(survivor.y).toBe(original!.y)
            expect(survivor.z).toBe(original!.z)
        }
        expect(after.some((dot) => dot.key === '5:4')).toBe(false)
    })

    // The consumed overlay removes exactly the tapped slot, and every surviving
    // dot keeps its key and position (no reshuffle).
    test('a consumed slot overlay drops that dot, others stay put', () => {
        const product = makeProduct({ id: 5, stock: 4 })
        const before = buildDots([product], [])
        const after = buildDots([product], [], new Map([[5, [1]]]))

        expect(before).toHaveLength(4)
        expect(after.map((dot) => dot.key)).toEqual(['5:0', '5:2', '5:3'])
        for (const survivor of after) {
            const original = before.find((dot) => dot.key === survivor.key)!
            expect(survivor.x).toBe(original.x)
            expect(survivor.y).toBe(original.y)
        }
    })

    // Category order must not depend on live stock, or consuming from one pile
    // could reorder categories and slide another pile sideways.
    test('consuming from one category leaves other categories put', () => {
        const dairy = makeCategory(10, 'Dairy')
        const fruit = makeCategory(20, 'Fruit')
        const before = buildDots(
            [
                makeProduct({ id: 1, stock: 3, category: dairy, category_id: 10 }),
                makeProduct({ id: 2, stock: 2, category: fruit, category_id: 20 }),
            ],
            [],
        )
        const after = buildDots(
            [
                makeProduct({ id: 1, stock: 2, category: dairy, category_id: 10 }),
                makeProduct({ id: 2, stock: 2, category: fruit, category_id: 20 }),
            ],
            [],
        )

        const fruitBefore = before.filter((dot) => dot.productId === 2)
        const fruitAfter = after.filter((dot) => dot.productId === 2)
        expect(fruitAfter).toEqual(fruitBefore)
    })
})
