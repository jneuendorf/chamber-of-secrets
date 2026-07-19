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

import { api, type Profile } from './api/client'
import { activeProfileId } from './profiles'

/** The active profile with its live xp/level/streaks. `null` = none selected. */
export const activeProfile = writable<Profile | null>(null)

/** Set when a refresh observes a higher level; the UI clears it after celebrating. */
export const levelUp = writable<number | null>(null)

/** Level of the active profile (1 when none is selected). */
export const level = derived(activeProfile, (profile) => profile?.level ?? 1)

/** Re-read the active profile so XP/level/streak reflect the latest movements. */
export async function refreshProfile(): Promise<void> {
    const id = get(activeProfileId)
    if (id == null) {
        activeProfile.set(null)
        return
    }
    // ponytail: no GET /profiles/{id} — the list is a handful of rows on a home LAN.
    const profiles = await api.profiles.list(true)
    const found = profiles.find((profile) => profile.id === id) ?? null
    const previous = get(activeProfile)
    if (previous && found && found.level > previous.level) {
        levelUp.set(found.level)
    }
    activeProfile.set(found)
}

// Keep the store in sync with the picker. Guarded like `profiles.ts`: no fetch
// during SSR or in tests, where there is no browser storage to select from.
if (typeof localStorage !== 'undefined') {
    activeProfileId.subscribe(() => {
        void refreshProfile()
    })
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
