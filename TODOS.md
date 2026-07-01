# Temporary migrations (due to pre-alpha WIP)

Code/spec misalignments found during review. Pre-users → no data
migration owed; this file tracks the *code* delta needed to bring the
implementation in line with the current spec in `FEATURES.md`.

Delete entries once landed. Keep the file and this header even when empty.
Larger consistency work is also tracked as ROADMAP WL-4.5.

---

## Visual consistency

- **Colour-token drift** (violates the WL-3.3 "never hardcode" rule):
  - [`scan/+page.svelte`](frontend/src/routes/scan/+page.svelte) uses Tailwind
    defaults `text-gray-100/200/300/400` instead of `ink-*` tokens.
  - [`chamber/+page.svelte`](frontend/src/routes/chamber/+page.svelte) uses
    literal gold `rgba(255, 215, 0, …)` throughout — add a `gold` accent token
    to `@theme` (`src/app.css`) and reference it.

## i18n

- **Untranslated strings in scan.**
  [`scan/+page.svelte`](frontend/src/routes/scan/+page.svelte) hardcodes
  `Category:` and `(new)` in English (≈ lines 349, 356). Extract to `en.json`
  / `de.json` like every other user-facing string.
