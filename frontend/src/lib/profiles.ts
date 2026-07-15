/**
 * Profiles (WL-5.1) — login-less, Netflix-style identity picker.
 *
 * The active profile id lives in `localStorage` and is sent with mutations by
 * the API client (see `ACTIVE_PROFILE_KEY` in `api/client.ts`). No server
 * session; the app stays fully usable with none selected.
 */
import { writable } from 'svelte/store'

import { ACTIVE_PROFILE_KEY } from './api/client'
import { AVATAR_PALETTE } from './theme'

/**
 * Preset avatar bases. Keys are the **stable part ids** persisted in
 * `avatar_config.base`; values are the emoji stand-in used until WL-5.4 ships
 * real SVG parts.
 *
 * Store the id, never the glyph or SVG markup: the id decouples the data from
 * the art, so a part can be redrawn — or swapped from emoji to SVG — without
 * touching a single stored profile.
 */
export const AVATAR_BASES: Record<string, string> = {
    fox: '🦊',
    bear: '🐻',
    rabbit: '🐰',
    panda: '🐼',
    owl: '🦉',
    frog: '🐸',
    cat: '🐱',
    monkey: '🐵',
}

export const AVATAR_BASE_IDS = Object.keys(AVATAR_BASES)

export { AVATAR_PALETTE }

/** Resolve a stored base id to its glyph. Unknown ids (a part from a newer
 * version, or legacy data) fall back rather than rendering blank. */
export function avatarGlyph(base: string | undefined | null): string {
    return (base && AVATAR_BASES[base]) || AVATAR_BASES[AVATAR_BASE_IDS[0]]
}

export function defaultAvatarConfig(): { base: string; color: string } {
    return { base: AVATAR_BASE_IDS[0], color: AVATAR_PALETTE[0] }
}

function readStored(): number | null {
    if (typeof localStorage === 'undefined') {
        return null
    }
    const raw = localStorage.getItem(ACTIVE_PROFILE_KEY)
    return raw ? Number(raw) : null
}

/** Active profile id, persisted to localStorage. `null` = no profile selected. */
export const activeProfileId = writable<number | null>(readStored())

activeProfileId.subscribe((id) => {
    if (typeof localStorage === 'undefined') {
        return
    }
    if (id == null) {
        localStorage.removeItem(ACTIVE_PROFILE_KEY)
    } else {
        localStorage.setItem(ACTIVE_PROFILE_KEY, String(id))
    }
})
