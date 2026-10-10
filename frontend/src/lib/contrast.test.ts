/**
 * Contrast audit (WL-6.4): every text/surface pairing the app uses must meet
 * WCAG AA in both themes — 4.5:1 for text, 3:1 for UI parts (borders, focus
 * rings). Reads the tokens straight from `app.css`, so retinting a token that
 * breaks legibility fails here. These ratios are also the art brief's floor.
 */
import { describe, expect, test } from 'bun:test'
import { readFileSync } from 'node:fs'

const css = readFileSync(new URL('../app.css', import.meta.url), 'utf8')

type Scheme = 'light' | 'dark'

const tokens = new Map<string, Record<Scheme, string>>()
for (const match of css.matchAll(
    /--color-([\w-]+):\s*(?:light-dark\((#\w+),\s*(#\w+)\)|(#\w+))/g,
)) {
    const [, name, light, dark, both] = match
    tokens.set(name, { light: light ?? both, dark: dark ?? both })
}

function hex(token: string, scheme: Scheme): string {
    if (token === 'white') {
        return '#ffffff'
    }
    const pair = tokens.get(token)
    if (!pair) {
        throw new Error(`unknown token ${token}`)
    }
    return pair[scheme]
}

function luminance(color: string): number {
    const channels = [1, 3, 5].map((offset) => {
        const value = Number.parseInt(color.slice(offset, offset + 2), 16) / 255
        return value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4
    })
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]
}

function contrast(first: string, second: string): number {
    const [lighter, darker] = [luminance(first), luminance(second)].sort(
        (left, right) => right - left,
    )
    return (lighter + 0.05) / (darker + 0.05)
}

const SURFACES = ['bark-850', 'bark-800', 'bark-950', 'ink-900', 'backdrop-center']
const TEXT = [
    'ink-100',
    'ink-200',
    'ink-250',
    'ink-300',
    'ink-400',
    'ink-500',
    'accent-100',
    'accent-300',
    'danger-300',
    'danger-200',
    'success-300',
    'warning-400',
    'info-400',
]

// [foreground, background] pairs used outside the plain surface grid.
const FILLS: [string, string][] = [
    ['white', 'accent-900'],
    ['white', 'accent-700'],
    ['white', 'danger-500'],
    ['white', 'success-700'],
    ['danger-200', 'danger-900'],
    ['success-200', 'success-900'],
    ['success-100', 'success-800'],
    ['success-900', 'success-100'],
    ['accent-900', 'warning-550'],
]

// Non-text UI parts (WCAG 1.4.11): focus rings and the Pantry-dex card edge.
const UI_PARTS: [string, string][] = [
    ['accent-500', 'bark-850'],
    ['gold', 'bark-850'],
]

describe.each(['light', 'dark'] as Scheme[])('%s theme', (scheme) => {
    const ratio = (fg: string, bg: string) => contrast(hex(fg, scheme), hex(bg, scheme))

    test.each(
        TEXT.flatMap((fg) => SURFACES.map((bg) => [fg, bg])),
    )('text %s on %s ≥ 4.5', (fg, bg) =>
        expect(ratio(fg, bg)).toBeGreaterThanOrEqual(4.5))

    test.each(FILLS)('text %s on %s ≥ 4.5', (fg, bg) =>
        expect(ratio(fg, bg)).toBeGreaterThanOrEqual(4.5))

    test.each(UI_PARTS)('ui %s on %s ≥ 3', (fg, bg) =>
        expect(ratio(fg, bg)).toBeGreaterThanOrEqual(3))
})

test('contrast matches the WCAG reference values', () => {
    expect(contrast('#000000', '#ffffff')).toBeCloseTo(21)
    expect(contrast('#777777', '#ffffff')).toBeCloseTo(4.48, 2)
})
