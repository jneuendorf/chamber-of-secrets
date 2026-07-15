import { describe, expect, test } from 'bun:test'

import {
    AVATAR_BASE_IDS,
    AVATAR_BASES,
    avatarGlyph,
    defaultAvatarConfig,
} from './profiles.ts'

describe('avatar presets', () => {
    test('resolves a stored part id to its glyph', () => {
        expect(avatarGlyph('fox')).toBe('🦊')
        expect(avatarGlyph('bear')).toBe('🐻')
    })

    test('falls back for unknown, legacy, or missing ids', () => {
        const fallback = AVATAR_BASES[AVATAR_BASE_IDS[0]]
        // A part id from a newer version, a legacy glyph written before ids, and
        // an absent value must all render something rather than blank.
        expect(avatarGlyph('wizard-hat')).toBe(fallback)
        expect(avatarGlyph('🦊')).toBe(fallback)
        expect(avatarGlyph(undefined)).toBe(fallback)
        expect(avatarGlyph(null)).toBe(fallback)
        expect(avatarGlyph('')).toBe(fallback)
    })

    test('defaults store an id, never a glyph', () => {
        const config = defaultAvatarConfig()
        expect(AVATAR_BASE_IDS).toContain(config.base)
        expect(Object.values(AVATAR_BASES)).not.toContain(config.base)
    })
})
