import { describe, expect, test } from 'bun:test'

import type { Category } from '$lib/api/client'
import { resolveIcon, resolveRestockPolicy, stockStatus } from './category'

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

describe('resolveRestockPolicy', () => {
    test('returns nulls for null/undefined category', () => {
        expect(resolveRestockPolicy(null, [])).toEqual({
            target: null,
            min: null,
            targetFrom: null,
            minFrom: null,
        })
        expect(resolveRestockPolicy(undefined, [])).toEqual({
            target: null,
            min: null,
            targetFrom: null,
            minFrom: null,
        })
    })

    test('uses own thresholds when set', () => {
        const cat = makeCategory({
            id: 1,
            name: 'Dairy',
            restock_target: 4,
            restock_min: 2,
        })
        expect(resolveRestockPolicy(cat, [cat])).toEqual({
            target: 4,
            min: 2,
            targetFrom: 1,
            minFrom: 1,
        })
    })

    test('inherits each field independently from nearest ancestor', () => {
        const parent = makeCategory({
            id: 1,
            name: 'Food',
            restock_target: 6,
            restock_min: 3,
        })
        const child = makeCategory({
            id: 2,
            name: 'Milk',
            parent_id: 1,
            restock_min: 1,
        })
        expect(resolveRestockPolicy(child, [parent, child])).toEqual({
            target: 6,
            min: 1,
            targetFrom: 1,
            minFrom: 2,
        })
    })

    test('stops inheriting when restock_inherit is false', () => {
        const parent = makeCategory({ id: 1, name: 'Food', restock_target: 6 })
        const child = makeCategory({
            id: 2,
            name: 'Milk',
            parent_id: 1,
            restock_inherit: false,
        })
        expect(resolveRestockPolicy(child, [parent, child])).toEqual({
            target: null,
            min: null,
            targetFrom: null,
            minFrom: null,
        })
    })

    test('handles circular parent references gracefully', () => {
        const a = makeCategory({ id: 1, name: 'A', parent_id: 2 })
        const b = makeCategory({ id: 2, name: 'B', parent_id: 1 })
        expect(resolveRestockPolicy(a, [a, b])).toEqual({
            target: null,
            min: null,
            targetFrom: null,
            minFrom: null,
        })
    })
})

describe('stockStatus', () => {
    const noPolicy = { target: null, min: null, targetFrom: null, minFrom: null }

    test('out when stock is zero or negative', () => {
        expect(stockStatus(0, { ...noPolicy, target: 4 })).toBe('out')
        expect(stockStatus(-1, noPolicy)).toBe('out')
    })

    test('low when below min', () => {
        expect(stockStatus(1, { ...noPolicy, min: 2 })).toBe('low')
    })

    test('low when under target', () => {
        expect(stockStatus(3, { ...noPolicy, target: 5 })).toBe('low')
    })

    test('ok when at or above thresholds', () => {
        expect(stockStatus(5, { ...noPolicy, target: 5, min: 2 })).toBe('ok')
    })

    test('ok when no thresholds configured', () => {
        expect(stockStatus(1, noPolicy)).toBe('ok')
    })
})
