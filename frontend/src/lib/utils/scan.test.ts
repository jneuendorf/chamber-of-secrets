import { describe, expect, test } from 'bun:test'

import {
    buildProductPayload,
    clampQuantity,
    isPlausibleBarcode,
    parseLookupCategory,
} from './scan.ts'

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

describe('buildProductPayload', () => {
    test('blank EAN becomes null so manual products do not collide', () => {
        const payload = buildProductPayload(
            { ean: '', name: 'Bakery roll', brand: null, image_url: null },
            'Unknown',
            null,
        )
        expect(payload.ean).toBeNull()
    })

    test('keeps a real EAN', () => {
        const payload = buildProductPayload(
            { ean: '4001234567890', name: 'Milk', brand: null, image_url: null },
            'Unknown',
            3,
        )
        expect(payload.ean).toBe('4001234567890')
        expect(payload.category_id).toBe(3)
    })

    test('trims fields and falls back to name when blank', () => {
        const payload = buildProductPayload(
            { ean: '', name: '   ', brand: '  Acme ', image_url: ' http://x/y.png ' },
            'Unknown Product',
            null,
        )
        expect(payload.name).toBe('Unknown Product')
        expect(payload.brand).toBe('Acme')
        expect(payload.image_url).toBe('http://x/y.png')
    })

    test('empty optional fields become null', () => {
        const payload = buildProductPayload(
            { ean: '', name: 'X', brand: '  ', image_url: '' },
            'Unknown',
            null,
        )
        expect(payload.brand).toBeNull()
        expect(payload.image_url).toBeNull()
    })
})

describe('isPlausibleBarcode', () => {
    test('accepts EAN-8 / UPC-E / UPC-A / EAN-13 lengths', () => {
        expect(isPlausibleBarcode('123456')).toBe(true) // UPC-E (6)
        expect(isPlausibleBarcode('12345678')).toBe(true) // EAN-8 (8)
        expect(isPlausibleBarcode('036000291452')).toBe(true) // UPC-A (12)
        expect(isPlausibleBarcode('4001234567890')).toBe(true) // EAN-13 (13)
    })

    test('rejects the OFF placeholder and other short codes', () => {
        expect(isPlausibleBarcode('1234')).toBe(false)
        expect(isPlausibleBarcode('123456789')).toBe(false) // 9 digits
        expect(isPlausibleBarcode('')).toBe(false)
    })

    test('rejects non-digit input', () => {
        expect(isPlausibleBarcode('12345abc')).toBe(false)
        expect(isPlausibleBarcode('4001234 67890')).toBe(false)
    })
})
