/**
 * Shared theme helpers.
 *
 * UI colours live as Tailwind v4 `@theme` tokens in `src/app.css` (e.g.
 * `--color-ink-100`, `--color-bark-600`). Chart.js draws to a `<canvas>` and
 * needs raw colour strings rather than CSS classes, so `themeColor` resolves a
 * token to its value at runtime and `CHART_PALETTE` keeps the categorical
 * series colours in one place (previously duplicated inline in each chart).
 */

/** Resolve a Tailwind `@theme` colour token (e.g. 'ink-100') to its value. */
export function themeColor(token: string): string {
    if (typeof document === 'undefined') {
        return ''
    }
    return getComputedStyle(document.documentElement)
        .getPropertyValue(`--color-${token}`)
        .trim()
}

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
