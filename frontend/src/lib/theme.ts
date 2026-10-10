/**
 * Theme (WL-3.3) — light/dark selection and color access from code.
 *
 * UI colors are `light-dark()` pairs in `src/app.css`; picking a theme only sets
 * `data-theme` on <html>, and CSS does the rest. Chart.js draws to a `<canvas>`
 * and needs raw color strings, so `themeColor` resolves a token for a given
 * scheme and `CHART_PALETTE` keeps the categorical series colors in one place.
 */
import { derived, writable } from 'svelte/store'

export type ThemePreference = 'system' | 'light' | 'dark'
export type ColorScheme = 'light' | 'dark'

/** Also read by the pre-paint script in `app.html` — keep the two in sync. */
export const THEME_KEY = 'theme'

const PREFERENCES: ThemePreference[] = ['system', 'light', 'dark']

/** Anything unknown (nothing stored, a stale value) means "follow the system". */
export function parsePreference(stored: string | null): ThemePreference {
    return PREFERENCES.includes(stored as ThemePreference)
        ? (stored as ThemePreference)
        : 'system'
}

/** The toggle's order: one tap per step, wrapping around. */
export function nextPreference(current: ThemePreference): ThemePreference {
    return PREFERENCES[(PREFERENCES.indexOf(current) + 1) % PREFERENCES.length]
}

export const themePreference = writable<ThemePreference>(
    parsePreference(
        typeof localStorage === 'undefined' ? null : localStorage.getItem(THEME_KEY),
    ),
)

// Guarded like `profiles.ts`: no DOM or storage during SSR or in tests.
if (typeof document !== 'undefined') {
    themePreference.subscribe((preference) => {
        if (preference === 'system') {
            delete document.documentElement.dataset.theme
            localStorage.removeItem(THEME_KEY)
        } else {
            document.documentElement.dataset.theme = preference
            localStorage.setItem(THEME_KEY, preference)
        }
    })
}

/** The scheme actually showing — the preference, or the OS setting under "system". */
export const colorScheme = derived<typeof themePreference, ColorScheme>(
    themePreference,
    (preference, set) => {
        if (preference !== 'system') {
            set(preference)
            return
        }
        if (typeof matchMedia === 'undefined') {
            set('dark')
            return
        }
        const query = matchMedia('(prefers-color-scheme: light)')
        const update = () => set(query.matches ? 'light' : 'dark')
        update()
        query.addEventListener('change', update)
        return () => query.removeEventListener('change', update)
    },
    'dark',
)

/**
 * Resolve a color token (e.g. 'ink-100') to an `rgb()` string under `scheme`.
 * The custom property itself holds an unresolved `light-dark()` pair, so the
 * token is applied to a probe element and read back. Taking `scheme` as an
 * argument is what lets a chart `$effect` redraw when the theme changes.
 */
export function themeColor(token: string, scheme: ColorScheme): string {
    if (typeof document === 'undefined') {
        return ''
    }
    const probe = document.createElement('span')
    probe.style.colorScheme = scheme
    probe.style.color = `var(--color-${token})`
    document.body.append(probe)
    const color = getComputedStyle(probe).color
    probe.remove()
    return color
}

/** Playful preset colors for profile avatars (raw strings — stored in
 * `avatar_config.color` and painted as inline backgrounds, not theme utilities). */
export const AVATAR_PALETTE = [
    '#e8a33d',
    '#e74c3c',
    '#3498db',
    '#2ecc71',
    '#9b59b6',
    '#1abc9c',
    '#e67e22',
    '#e91e63',
]

/** Categorical palette for chart series (distinct hues; order = series order). */
export const CHART_PALETTE = [
    '#e74c3c',
    '#3498db',
    '#2ecc71',
    '#f39c12',
    '#9b59b6',
    '#1abc9c',
    '#e67e22',
    '#e91e63',
    '#34495e',
    '#1a1a2e',
]
