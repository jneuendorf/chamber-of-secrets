# Temporary migrations (due to pre-alpha WIP)

Code/spec misalignments found during review. Pre-users → no data
migration owed; this file tracks the *code* delta needed to bring the
implementation in line with the current spec in `FEATURES.md`.

Delete entries once landed. Keep the file and this header even when empty.
Larger consistency work is also tracked as ROADMAP WL-4.5.

---

## Semantic correctness

- **Inventory "low stock" ignores category thresholds.**
  [`inventory/+page.svelte`](frontend/src/routes/inventory/+page.svelte)
  flags low/out with a hardcoded `stock <= 1` / `<= 0`, but categories carry
  `restock_min`/`restock_target` (with inheritance) that drive
  `/api/analytics/restock-overview`. Two competing notions of "low". Use the
  effective (inherited) category thresholds for the badge so the inventory
  list and the restock overview agree.

- **Chamber "Required" stat is mislabeled.**
  [`chamber/+page.svelte`](frontend/src/routes/chamber/+page.svelte) labels
  the *depleted* count (stock ≤ 0) as "required". Either relabel it
  "Depleted", or compute the real count of items below their restock
  threshold (preferred — ties into the unified low-stock definition above).

## Visual consistency

- **Three modal implementations.** WL-3.4 standardised categories/analytics
  on the Bits UI `Modal`, but
  [`BarcodeScanner.svelte`](frontend/src/lib/components/BarcodeScanner.svelte)
  (camera modal) and [`chamber/+page.svelte`](frontend/src/routes/chamber/+page.svelte)
  (stats modal) still hand-roll their own backdrops. Migrate both to the
  `Modal` component (or document why a given one can't).

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
