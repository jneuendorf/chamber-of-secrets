import { describe, expect, test } from 'bun:test'

import { CHAMBER_STAGES, chamberStage, guardianMood } from './progression'

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
