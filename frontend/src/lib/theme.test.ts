import { describe, expect, test } from 'bun:test'

import { nextPreference, parsePreference } from './theme'

describe('parsePreference', () => {
    test('keeps a valid stored preference', () => {
        expect(parsePreference('light')).toBe('light')
        expect(parsePreference('dark')).toBe('dark')
        expect(parsePreference('system')).toBe('system')
    })

    test('falls back to system for nothing stored or junk', () => {
        expect(parsePreference(null)).toBe('system')
        expect(parsePreference('sepia')).toBe('system')
    })
})

describe('nextPreference', () => {
    test('cycles system → light → dark → system', () => {
        expect(nextPreference('system')).toBe('light')
        expect(nextPreference('light')).toBe('dark')
        expect(nextPreference('dark')).toBe('system')
    })
})
