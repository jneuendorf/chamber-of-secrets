import { afterEach, describe, expect, test } from 'bun:test'

import { HAND_KEY, hand, parseHand } from './hand'

afterEach(() => hand.set('right'))

describe('handedness', () => {
    test('anything but "left" means right', () => {
        expect(parseHand('left')).toBe('left')
        expect(parseHand(null)).toBe('right')
        expect(parseHand('sideways')).toBe('right')
    })

    test('left marks <html> and persists; right clears both', () => {
        hand.set('left')
        expect(document.documentElement.dataset.hand).toBe('left')
        expect(localStorage.getItem(HAND_KEY)).toBe('left')
        hand.set('right')
        expect(document.documentElement.dataset.hand).toBeUndefined()
        expect(localStorage.getItem(HAND_KEY)).toBeNull()
    })
})
