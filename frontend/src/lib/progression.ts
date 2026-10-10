/**
 * Progression (WL-5.3) — the one primitive every gamification feature reads from.
 *
 * XP and streaks are awarded server-side on each attributed movement
 * (`services/progression.py`); this mirrors the active profile and derives the
 * chamber's visual state from it. Deliberately **design-agnostic**: it yields a
 * stage number and a mood name, never art — the scene renders them as data
 * attributes so WL-5.5 can attach whatever it likes without touching this file.
 */
import { derived, get, writable } from 'svelte/store'

import { ApiError, api, type Profile, type RewardTier } from './api/client'
import { activeProfileId } from './profiles'

/** The active profile with its live xp/level/streaks. `null` = none selected. */
export const activeProfile = writable<Profile | null>(null)

/**
 * The level crossing a refresh observed, or `null`. Carries `from` as well as
 * `to` because a single movement can span several levels, and the rewards it
 * unlocked are the ones in that whole range (WL-5.7). The UI clears it after
 * celebrating, which is also the once-per-crossing guard: the next refresh sees
 * an unchanged level and sets nothing.
 */
export type LevelCrossing = { from: number; to: number }

export const levelUp = writable<LevelCrossing | null>(null)

/** Badge keys earned since the last refresh; the UI clears them after celebrating. */
export const newAchievements = writable<string[]>([])

/** Level of the active profile (1 when none is selected). */
export const level = derived(activeProfile, (profile) => profile?.level ?? 1)

/** Re-read the active profile so XP/level/streak reflect the latest movements. */
export async function refreshProfile(): Promise<void> {
    const id = get(activeProfileId)
    if (id == null) {
        activeProfile.set(null)
        return
    }
    // A stored id whose profile is gone (e.g. a reset database) means "none selected".
    const found = await api.profiles.get(id).catch((err: unknown) => {
        if (err instanceof ApiError && err.isNotFound) {
            return null
        }
        throw err
    })
    // Diffed here rather than returned by the mutation: every award path
    // (transactions, OFF contributions) lands in the same refresh.
    const { crossing, earned } = progressSince(get(activeProfile), found)
    if (crossing) {
        levelUp.set(crossing)
    }
    if (earned.length > 0) {
        newAchievements.set(earned)
    }
    activeProfile.set(found)
}

/**
 * What one profile gained between two snapshots of it. Only the *same* profile
 * counts: switching the picker to someone further along is not a level-up, and
 * their existing badges are not newly earned.
 */
export function progressSince(
    previous: Profile | null,
    found: Profile | null,
): { crossing: LevelCrossing | null; earned: string[] } {
    if (!previous || !found || previous.id !== found.id) {
        return { crossing: null, earned: [] }
    }
    return {
        crossing:
            found.level > previous.level
                ? { from: previous.level, to: found.level }
                : null,
        earned: found.achievements.filter(
            (key) => !previous.achievements.includes(key),
        ),
    }
}

// Keep the store in sync with the picker. Guarded like `profiles.ts`: no fetch
// during SSR or in tests, where there is no browser storage to select from.
if (typeof localStorage !== 'undefined') {
    activeProfileId.subscribe(() => {
        void refreshProfile()
    })
}

/**
 * Badge catalog (WL-5.4) — display order and stand-in art. Keys mirror
 * `services/achievements.py`; names/descriptions live in the locales. The glyphs
 * are placeholders in the same spirit as the avatar emoji: swap the map when
 * WL-5.5 draws real badges, no stored data changes.
 */
export const ACHIEVEMENT_GLYPH: Record<string, string> = {
    first_scan: '🔍',
    stocked_50: '📦',
    streak_7: '🔥',
    level_5: '⭐',
    explorer: '🗺️',
}

export const ACHIEVEMENT_KEYS = Object.keys(ACHIEVEMENT_GLYPH)

/** Unknown keys (a badge from a newer backend) still render rather than blanking. */
export function achievementGlyph(key: string): string {
    return ACHIEVEMENT_GLYPH[key] ?? '🏅'
}

/**
 * XP at which a level begins — the inverse of the backend's `level_for_xp`
 * (`level = floor(sqrt(xp / 100)) + 1`). `xpForLevel(2) === 100`. Used to draw
 * progress toward the next level from the `xp`/`level` the API already returns.
 */
export function xpForLevel(level: number): number {
    return (Math.max(1, level) - 1) ** 2 * 100
}

/**
 * Reward tiers a level crossing just unlocked (WL-5.7): `from < level <= to`.
 * Half-open at the bottom so the level you were already on doesn't re-announce,
 * inclusive at the top so the level you just reached does. Several levels can be
 * crossed by one movement, so this returns a list, ordered by level.
 *
 * Announcing only — the *display* side stays the plain `level >= tier.level`
 * derivation on the profile page.
 */
export function rewardsUnlockedBetween(
    from: number,
    to: number,
    tiers: RewardTier[],
): RewardTier[] {
    return tiers
        .filter((tier) => tier.level > from && tier.level <= to)
        .sort((first, second) => first.level - second.level)
}

/** How built-out the chamber looks. Grows with level, then plateaus. */
export const CHAMBER_STAGES = 5

export function chamberStage(level: number): number {
    return Math.max(1, Math.min(CHAMBER_STAGES, Math.ceil(level / 2)))
}

/** How the guardian feels about the pantry — formalises the old 🏚️ empty state. */
export type GuardianMood = 'thriving' | 'content' | 'sparse' | 'forlorn'

/**
 * Mood from how well stocked the chamber is: the share of tracked products that
 * need restocking, with an empty chamber always forlorn.
 */
export function guardianMood(
    trackedProducts: number,
    needsRestock: number,
    totalItems: number,
): GuardianMood {
    if (trackedProducts === 0 || totalItems === 0) {
        return 'forlorn'
    }
    const lacking = needsRestock / trackedProducts
    if (lacking <= 0.1) {
        return 'thriving'
    }
    if (lacking <= 0.4) {
        return 'content'
    }
    return 'sparse'
}
