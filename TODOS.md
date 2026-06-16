# Temporary migrations (due to pre-alpha WIP)

Code/spec misalignments found during review. Pre-users → no data
migration owed; this file tracks the *code* delta needed to bring the
implementation in line with the current spec in `FEATURES.md`.

Delete entries once landed. Keep the file and this header even when empty.

---

### T1. Analytics page typecheck errors *(Chart.js `cutout` property)*

`svelte-check` reports 3 errors in `analytics/+page.svelte`: the
`cutout` property is not recognised in Chart.js type definitions.
Likely a version mismatch or missing type assertion.

**Files**: `frontend/src/routes/analytics/+page.svelte`.

### T2. API client error handling *(no 4xx/5xx differentiation)*

`frontend/src/lib/api/client.ts` throws a generic `Error` on any
non-OK response. The scan page can't distinguish "product not found"
(404) from "server down" (500). Needs typed error classes or at least
status-aware error messages.

**Files**: `frontend/src/lib/api/client.ts`, callers in `+page.svelte`
files.
