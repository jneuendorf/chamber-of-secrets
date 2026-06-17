# Chamber of Secrets — Agent Instructions

Household grocery companion — scan, track, cook, shop.
Runs on a Raspberry Pi, accessible via mobile over HTTPS.
See `FEATURES.md` (scope + core principles), `ROADMAP.md` (status),
`TODOS.md` (code/spec misalignments needing immediate attention).

Core principles (in priority order): **easy to use** > **fun to use** >
lightweight > portable. Every feature must pass: *would a 10-year-old
use this without being told to?*

## Workflow

- Tackle **at most one WL-\* item from `ROADMAP.md` per change**.
  Small commit scopes.
- Don't auto-commit, but suggest a commit message.
  Once a workload is done thoroughly, suggest a commit message to the user.
  Always let me review the changes and commit only after explicit approval.
- Reflect every status change in `ROADMAP.md` (✅ done · 🚧 in
  progress · ⬜ not started).
- **Docs must stay in sync with code.** If a feature is implemented,
  `FEATURES.md` must describe its actual state — not aspirational.
  If code and spec diverge, add an entry to `TODOS.md` and fix it
  before moving to new features. `TODOS.md` items take priority over
  new roadmap work. Delete entries once landed — don't keep struck-through
  items.
- **Test-driven**: critical functionality MUST be tested. Target >90%
  coverage. Frontend tests use `bun test`. Write tests before or
  alongside implementation, not as an afterthought.
- Run `just check-frontend` (lint + typecheck + test) or `just check-backend`, 
  respectively, before declaring done.
- Use `just lint-frontend` / `just format-frontend` for quick checks
  on staged files. Pass `""` to check all files instead:
  `just lint-frontend ""`.
- Run `just format-frontend` if linting reports formatting issues
  instead of reformatting yourself.

## Commits

Conventional Commits. Scope = layer (`frontend`, `backend`).
Multi-scope allowed but unfavored — split when feasible.

```
feat(frontend): add category picker to scan page
fix(backend): handle missing EAN gracefully
feat(frontend,backend): WL-2.3 manual image upload
```

Body very concise: state changes not intentions.
Bullet list ok. No co-author trailer unless asked.

## Architecture

- `backend/` — FastAPI + SQLAlchemy 2 + Alembic + SQLite. Python, uv.
- `frontend/` — SvelteKit 2 + Svelte 5 + TypeScript + Tailwind CSS 4. Bun.
- `compose.yaml` — Docker/Podman stack with nginx (TLS via mkcert).

## Conventions

- **Package manager**: Bun (never npm/yarn/pnpm).
- **Backend tooling**: uv + ruff (lint + format).
- **Frontend tooling**: Biome v2 (lint + format). 4-space indent app code,
  2-space configs/JSON/HTML/YAML, line width 88, single quotes,
  semicolons asNeeded, trailing commas all. Markdown formatting disabled.
- **Tailwind CSS v4** via `@tailwindcss/vite` (no config file).
  Entry point: `src/app.css`.
- **i18n**: svelte-i18n v4 (EN + DE). Keys: `nav.*`, `dashboard.*`,
  etc. Both locale files must stay in sync.
- Scoped `<style>` blocks coexist with Tailwind.

## Prohibited

- Don't bypass git hooks (`--no-verify`) or `--amend` without ask.
- Don't use npm/yarn/pnpm — only `bun`.
- Don't add Tailwind config files — v4 uses CSS-only config.

## Quick reference

```bash
just dev                      # backend + frontend in parallel
just check                    # biome check + typecheck + test (all layers)
just check-all                # same as check, but all files (not staged)
just check-frontend           # biome check + typecheck + test (frontend)
just check-backend            # lint + test (backend, needs uv)
just test                     # all tests
just test-frontend            # bun test
just test-backend             # backend unit tests
just lint                     # biome + ruff lint (staged by default)
just lint-frontend            # biome lint (staged by default)
just lint-backend             # ruff lint
just format                   # biome + ruff format (staged by default)
just format-frontend          # biome format (staged by default)
just format-backend           # ruff format
just format-check             # check without writing (staged by default)
just typecheck-frontend       # svelte-check only
just seed                     # seed DB with sample data
just up                       # containerized prod stack
```
