/**
 * Handedness (WL-6.7) — which thumb the reach-critical controls sit under.
 *
 * Like the theme: the choice only sets `data-hand="left"` on <html>, and CSS
 * mirrors the controls (the `left-hand:` variant in `src/app.css`, or
 * `:global([data-hand='left'])` in scoped styles). Right is the default and
 * leaves no trace in storage or on <html>.
 */
import { writable } from 'svelte/store'

export type Hand = 'right' | 'left'

/** Also read by the pre-paint script in `app.html` — keep the two in sync. */
export const HAND_KEY = 'hand'

export function parseHand(stored: string | null): Hand {
    return stored === 'left' ? 'left' : 'right'
}

export const hand = writable<Hand>(
    parseHand(
        typeof localStorage === 'undefined' ? null : localStorage.getItem(HAND_KEY),
    ),
)

// Guarded like `theme.ts`: no DOM or storage during SSR.
if (typeof document !== 'undefined') {
    hand.subscribe((value) => {
        if (value === 'left') {
            document.documentElement.dataset.hand = 'left'
            localStorage.setItem(HAND_KEY, 'left')
        } else {
            delete document.documentElement.dataset.hand
            localStorage.removeItem(HAND_KEY)
        }
    })
}
