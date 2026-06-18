import { describe, expect, test } from 'bun:test'

import type { Category } from '$lib/api/client'
import { resolveIcon } from './category'

function makeCategory(
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

describe('resolveIcon', () => {
    test('returns null for null/undefined category', () => {
        expect(resolveIcon(null, [])).toBeNull()
        expect(resolveIcon(undefined, [])).toBeNull()
    })

    test('returns own icon if set', () => {
        const cat = makeCategory({ id: 1, name: 'Dairy', icon: '🥛' })
        expect(resolveIcon(cat, [cat])).toBe('🥛')
    })

    test('returns null when no icon in chain', () => {
        const cat = makeCategory({ id: 1, name: 'Food' })
        expect(resolveIcon(cat, [cat])).toBeNull()
    })

    test('inherits icon from parent', () => {
        const parent = makeCategory({ id: 1, name: 'Food', icon: '🍽️' })
        const child = makeCategory({ id: 2, name: 'Dairy', parent_id: 1 })
        expect(resolveIcon(child, [parent, child])).toBe('🍽️')
    })

    test('inherits icon from grandparent', () => {
        const grandparent = makeCategory({ id: 1, name: 'Food', icon: '🍽️' })
        const parent = makeCategory({ id: 2, name: 'Dairy', parent_id: 1 })
        const child = makeCategory({ id: 3, name: 'Milk', parent_id: 2 })
        expect(resolveIcon(child, [grandparent, parent, child])).toBe('🍽️')
    })

    test('prefers closest ancestor icon', () => {
        const grandparent = makeCategory({ id: 1, name: 'Food', icon: '🍽️' })
        const parent = makeCategory({ id: 2, name: 'Dairy', parent_id: 1, icon: '🥛' })
        const child = makeCategory({ id: 3, name: 'Milk', parent_id: 2 })
        expect(resolveIcon(child, [grandparent, parent, child])).toBe('🥛')
    })

    test('handles circular parent references gracefully', () => {
        const a = makeCategory({ id: 1, name: 'A', parent_id: 2 })
        const b = makeCategory({ id: 2, name: 'B', parent_id: 1 })
        expect(resolveIcon(a, [a, b])).toBeNull()
    })

    test('handles missing parent gracefully', () => {
        const child = makeCategory({ id: 2, name: 'Orphan', parent_id: 999 })
        expect(resolveIcon(child, [child])).toBeNull()
    })
})
