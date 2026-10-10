import { describe, expect, test } from 'bun:test'

import type { Profile, RewardTier } from './api/client'
import en from './i18n/en.json'
import {
    ACHIEVEMENT_KEYS,
    achievementGlyph,
    CHAMBER_STAGES,
    chamberStage,
    guardianMood,
    progressSince,
    rewardsUnlockedBetween,
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

describe('progressSince', () => {
    // Only the fields the diff reads; the rest of a Profile is irrelevant here.
    const snapshot = (id: number, level: number, achievements: string[] = []) =>
        ({ id, level, achievements }) as unknown as Profile

    test('a higher level on the same profile is a crossing', () => {
        expect(progressSince(snapshot(1, 2), snapshot(1, 4)).crossing).toEqual({
            from: 2,
            to: 4,
        })
    })

    test('reports only badges that are new since the last snapshot', () => {
        const { earned } = progressSince(
            snapshot(1, 1, ['first_scan']),
            snapshot(1, 1, ['first_scan', 'explorer']),
        )
        expect(earned).toEqual(['explorer'])
    })

    test('an unchanged refetch announces nothing — the once-per-crossing guard', () => {
        const same = snapshot(1, 3, ['first_scan'])
        expect(progressSince(same, same)).toEqual({ crossing: null, earned: [] })
    })

    test('switching to a profile further along is not a level-up', () => {
        expect(
            progressSince(snapshot(1, 1), snapshot(2, 4, ['level_5', 'streak_7'])),
        ).toEqual({ crossing: null, earned: [] })
    })

    test('first load (no previous snapshot) stays quiet', () => {
        expect(progressSince(null, snapshot(1, 4, ['explorer']))).toEqual({
            crossing: null,
            earned: [],
        })
    })
})

describe('rewardsUnlockedBetween', () => {
    const tier = (id: number, level: number): RewardTier => ({
        id,
        level,
        description: `reward ${id}`,
    })
    // Two tiers share level 5 — the spec allows several rewards per level.
    const tiers = [tier(1, 2), tier(2, 5), tier(3, 5), tier(4, 9)]

    test('announces the tier at the level just reached', () => {
        expect(rewardsUnlockedBetween(1, 2, tiers).map((t) => t.id)).toEqual([1])
    })

    test('excludes the level already held — no re-announcing on the next crossing', () => {
        expect(rewardsUnlockedBetween(2, 4, tiers)).toEqual([])
        expect(rewardsUnlockedBetween(5, 8, tiers)).toEqual([])
    })

    test('one movement spanning several levels catches every tier in between', () => {
        expect(rewardsUnlockedBetween(1, 9, tiers).map((t) => t.id)).toEqual([
            1, 2, 3, 4,
        ])
    })

    test('orders by level regardless of how the API returned them', () => {
        const shuffled = [tier(4, 9), tier(1, 2), tier(3, 5)]
        expect(rewardsUnlockedBetween(1, 10, shuffled).map((t) => t.level)).toEqual([
            2, 5, 9,
        ])
    })

    test('nothing to announce without tiers, or when the level did not move', () => {
        expect(rewardsUnlockedBetween(1, 5, [])).toEqual([])
        expect(rewardsUnlockedBetween(5, 5, tiers)).toEqual([])
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
