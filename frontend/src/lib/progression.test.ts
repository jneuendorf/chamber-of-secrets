import { describe, expect, test } from 'bun:test'

import en from './i18n/en.json'
import {
    ACHIEVEMENT_KEYS,
    achievementGlyph,
    CHAMBER_STAGES,
    chamberStage,
    guardianMood,
    xpForLevel,
} from './progression'

/** Mirror of the backend `level_for_xp` — kept here only to prove the inverse. */
function levelForXp(xp: number): number {
    return Math.floor((Math.max(xp, 0) / 100) ** 0.5) + 1
}

describe('chamberStage', () => {
    test('starts at 1 and grows with level', () => {
        expect(chamberStage(1)).toBe(1)
        expect(chamberStage(3)).toBe(2)
        expect(chamberStage(5)).toBe(3)
    })

    test('plateaus at CHAMBER_STAGES', () => {
        expect(chamberStage(CHAMBER_STAGES * 2)).toBe(CHAMBER_STAGES)
        expect(chamberStage(999)).toBe(CHAMBER_STAGES)
    })

    test('never drops below 1 for bogus levels', () => {
        expect(chamberStage(0)).toBe(1)
        expect(chamberStage(-4)).toBe(1)
    })
})

describe('achievementGlyph', () => {
    test('resolves every catalog key', () => {
        for (const key of ACHIEVEMENT_KEYS) {
            expect(achievementGlyph(key)).toBeTruthy()
        }
    })

    test('falls back for a badge from a newer backend', () => {
        expect(achievementGlyph('zero_waste_week')).toBe('🏅')
    })

    test('every catalog key is named in the locales', () => {
        // A missing entry renders the raw key in the ledger, so catch it here.
        for (const key of ACHIEVEMENT_KEYS) {
            expect(
                en.achievement[key as keyof typeof en.achievement]?.name,
            ).toBeTruthy()
        }
    })
})

describe('xpForLevel', () => {
    test('matches the known thresholds', () => {
        expect(xpForLevel(1)).toBe(0)
        expect(xpForLevel(2)).toBe(100)
        expect(xpForLevel(3)).toBe(400)
        expect(xpForLevel(5)).toBe(1600)
        expect(xpForLevel(10)).toBe(8100)
    })

    test('is the inverse of level_for_xp: a level starts exactly at its floor', () => {
        for (let xp = 0; xp <= 5000; xp += 37) {
            const level = levelForXp(xp)
            expect(xpForLevel(level)).toBeLessThanOrEqual(xp)
            expect(xpForLevel(level + 1)).toBeGreaterThan(xp)
        }
    })
})

describe('guardianMood', () => {
    test('forlorn with nothing tracked or nothing left', () => {
        expect(guardianMood(0, 0, 0)).toBe('forlorn')
        expect(guardianMood(5, 5, 0)).toBe('forlorn')
    })

    test('thriving when almost nothing needs restocking', () => {
        expect(guardianMood(10, 1, 30)).toBe('thriving')
    })

    test('content in the middle, sparse when most items run low', () => {
        expect(guardianMood(10, 4, 12)).toBe('content')
        expect(guardianMood(10, 7, 8)).toBe('sparse')
    })
})
