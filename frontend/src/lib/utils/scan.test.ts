import { describe, expect, test } from 'bun:test'

import { clampQuantity, parseLookupCategory } from './scan.ts'

describe('clampQuantity', () => {
    test('returns 1 for NaN', () => {
        expect(clampQuantity(NaN)).toBe(1)
    })

    test('returns 1 for Infinity', () => {
        expect(clampQuantity(Infinity)).toBe(1)
    })

    test('returns 1 for -Infinity', () => {
        expect(clampQuantity(-Infinity)).toBe(1)
    })

    test('clamps to minimum of 1', () => {
        expect(clampQuantity(0)).toBe(1)
        expect(clampQuantity(-5)).toBe(1)
    })

    test('rounds to nearest integer', () => {
        expect(clampQuantity(2.3)).toBe(2)
        expect(clampQuantity(2.7)).toBe(3)
        expect(clampQuantity(2.5)).toBe(3)
    })

    test('passes through valid integers', () => {
        expect(clampQuantity(1)).toBe(1)
        expect(clampQuantity(5)).toBe(5)
        expect(clampQuantity(100)).toBe(100)
    })
})

describe('parseLookupCategory', () => {
    test('returns null for null/undefined/empty', () => {
        expect(parseLookupCategory(null)).toBeNull()
        expect(parseLookupCategory(undefined)).toBeNull()
        expect(parseLookupCategory('')).toBeNull()
    })

    test('extracts last comma-separated part', () => {
        expect(parseLookupCategory('Beverages, Dairy, Milk')).toBe('Milk')
    })

    test('capitalises first character', () => {
        expect(parseLookupCategory('dairy')).toBe('Dairy')
    })

    test('strips locale prefix (e.g. en:, de:)', () => {
        expect(parseLookupCategory('en:beverages, en:milk')).toBe('Milk')
        expect(parseLookupCategory('de:Getränke')).toBe('Getränke')
    })

    test('handles single category', () => {
        expect(parseLookupCategory('Snacks')).toBe('Snacks')
    })

    test('handles whitespace-only parts', () => {
        expect(parseLookupCategory('  ,  ,  ')).toBeNull()
    })

    test('handles mixed prefixed and non-prefixed', () => {
        expect(parseLookupCategory('en:food, Dairy')).toBe('Dairy')
    })

    test('returns null when all parts are empty after stripping', () => {
        expect(parseLookupCategory('en:, de:')).toBeNull()
    })
})
