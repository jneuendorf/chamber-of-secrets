# Temporary migrations (due to pre-alpha WIP)

Code/spec misalignments found during review. Pre-users → no data
migration owed; this file tracks the *code* delta needed to bring the
implementation in line with the current spec in `FEATURES.md`.

Delete entries once landed. Keep the file and this header even when empty.

---

### ~~T1. Add category DELETE endpoint~~ ✅ landed

`DELETE /api/categories/{id}` added. Rejects with 409 if products are
assigned; reparents children to the deleted category's parent. Five
tests added.

### T2. Frontend test infrastructure *(zero coverage)*

No test runner, no test files, no `test` script in `package.json`, no
justfile recipe. `AGENTS.md` mandates >90% coverage. Tracked as `WL-3.2`
in `ROADMAP.md`.

**Files**: `frontend/package.json`, `justfile`.

### T3. API client error handling *(no 4xx/5xx differentiation)*

`frontend/src/lib/api/client.ts` throws a generic `Error` on any
non-OK response. The scan page can't distinguish "product not found"
(404) from "server down" (500). Needs typed error classes or at least
status-aware error messages.

**Files**: `frontend/src/lib/api/client.ts`, callers in `+page.svelte`
files.
