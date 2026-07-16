# Chamber of Secrets — Agent Instructions

Household grocery companion — scan, track, cook, shop.
Runs on a Raspberry Pi, accessible via mobile over HTTPS.
See `FEATURES.md` (scope + core principles), `ROADMAP.md` (status),
`TODOS.md` (code/spec misalignments needing immediate attention).

Core principles (in priority order): **easy to use** > **fun to use** >
lightweight > portable. Every feature must pass: _would a 10-year-old
use this without being told to?_

## Workflow

- Tackle **at most one WL-\* item from `ROADMAP.md` per change**.
  Small commit scopes.
- **Never auto-commit.** When work is complete, generate a suggested
  commit message and stop — I review the changes and commit manually.
  Only run `git commit` (or `git push`) when I explicitly ask you to in
  that turn; prior approval does not carry over to later changes.
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
- **Backend tooling**: uv + ruff (lint + format) + ty (type check,
  matches the editor's language server).
- **Migrations (SQLite)**: SQLite has no `ALTER COLUMN` and only limited
  `DROP COLUMN`. Wrap such changes in `with op.batch_alter_table(...)`
  (table rebuild) — standalone `op.alter_column(... server_default=...)`
  or `op.drop_column(...)` fail at runtime even though `render_as_batch=True`
  makes autogenerate _look_ fine (that flag only affects rendering, not
  execution). `tests/test_migrations.py` runs `upgrade head` on a fresh DB
  to catch this.
- **Frontend tooling**: Biome v2 (lint + format) for JS/TS/JSON/CSS.
  4-space indent app code, 2-space configs/JSON/HTML/YAML, line width 88,
  single quotes, semicolons asNeeded, trailing commas all. Markdown
  formatting disabled.
- **Svelte formatting**: Biome cannot format `.svelte` files yet, so
  Prettier + `prettier-plugin-svelte` owns them. Config in
  `frontend/.prettierrc.json` mirrors the Biome rules (single quotes,
  no semicolons, trailing commas all, 4-space, width 88). Just run
  `just format-frontend` — it routes Biome to non-Svelte files and
  Prettier to `.svelte` files; don't hand-format Svelte. Biome still
  lints and organizes imports for `.svelte` (its formatter is disabled
  for them in `biome.jsonc`). Editor formatting is wired up in
  `.zed/settings.json` (needs the community Biome extension).
- **API types are generated, never hand-written.** The Pydantic schemas in
  `backend/app/schemas.py` are the single source of truth for the wire
  contract: FastAPI publishes them as OpenAPI, and
  `frontend/src/lib/api/schema.d.ts` is generated from that (`just types`).
  `client.ts` only aliases them (`export type Profile = Schemas['ProfileRead']`)
  so import sites stay stable. Never edit `schema.d.ts` by hand.
    - **Not committed** — it's derived data (`.gitignore`d; Biome skips it via
      `vcs.useIgnoreFile`). `typecheck-frontend` depends on `types`, so it
      regenerates on demand and can't go stale.
    - It's a `.d.ts`: declarations only, no runtime representation, impossible to
      value-import. **`svelte-check` is its only consumer.** `bun test`, `vite dev`,
      `vite build`, and the Docker image all erase the type-only import and run fine
      without the file — don't add `types` as a dependency of those "for safety",
      it just costs a second.
    - Response models: **don't give a field a default** unless it may genuinely be
      absent. `x: T | None = None` makes the generated client think the key is
      optional; if it's always serialized, write `x: T | None`.
    - SQLAlchemy models are the _DB_ schema, not the wire contract — don't try to
      sync them to TypeScript. The chain is SQLAlchemy → Pydantic (hand-written,
      deliberately) → OpenAPI → TS (generated).
- **Tailwind CSS v4** via `@tailwindcss/vite` (no config file).
  Entry point: `src/app.css`.
- **Canonical classes**: prefer v4's shorthand over an arbitrary bracket value
  when an exact equivalent exists:
    - bare numeric scale — `z-10000` not `z-[10000]`, `max-h-70` not
      `max-h-[280px]` (spacing is 0.25rem/unit, so `70` = 17.5rem = 280px)
    - CSS variables — `min-w-(--anchor-width)` not `min-w-[var(--anchor-width)]`
    - boolean `data-*` variants — `data-selected:` not `data-[selected]:`
      (values still need brackets: `data-[state=open]:`)

    Reserve `[…]` for values with no scale equivalent: one-off shadows,
    unitless line-heights, off-grid spacing.

- **Colors**: use the `@theme` tokens in `src/app.css`
  (`bark-*` surfaces, `ink-*` neutrals, `accent-*`, `danger/success/warning/info`)
  — never hardcode hex. In markup use the utilities (`bg-bark-850`,
  `text-ink-100`); in scoped `<style>` use `var(--color-…)`. Chart series
  colors live in `src/lib/theme.ts` (`CHART_PALETTE` + `themeColor()`), since
  canvas needs raw strings. App is dark-only for now (WL-3.3).
- **Headless UI**: [Bits UI](https://bits-ui.com) provides accessible
  primitives (`Select`, `Modal`→Dialog so far; Checkbox/Tabs/Tooltip/Date
  Picker as features need them). Style them with **Tailwind utility classes**
  (our `@theme` tokens) passed via `class` — _not_ scoped `<style>`: classes
  handed to a library component don't get Svelte's scope hash, so scoped
  selectors silently don't apply (Svelte flags them "unused"). Wrap new
  primitives behind a thin local component with a small typed API.
- **i18n**: svelte-i18n v4 (EN + DE). Keys: `nav.*`, `dashboard.*`,
  etc. Both locale files must stay in sync.
- Scoped `<style>` blocks coexist with Tailwind.
- **Naming**: avoid single-character variable names. Use descriptive
  names even for short-lived locals (e.g. `cat` not `c`, `err` not `e`).
- **American English** in docs, comments, and identifiers: `color` not
  `colour`, `standardize` not `standardise`, `behavior` not `behaviour`,
  `initialize`/`normalization`/`analyze`. This covers `.md` files, code
  comments, and the EN locale (user-facing copy). DE locale is unaffected.

## Prohibited

- Don't bypass git hooks (`--no-verify`) or `--amend` without ask.
- Don't use npm/yarn/pnpm — only `bun`.
- Don't add Tailwind config files — v4 uses CSS-only config.

## Quick reference

```bash
just dev                      # backend + frontend in parallel
just dev https                # same, but frontend over TLS (mkcert certs) for on-device camera
just check                    # biome check + typecheck + test (all layers)
just check-all                # same as check, but all files (not staged)
just check-frontend           # biome check + typecheck + test (frontend)
just check-backend            # lint + typecheck + test (backend, needs uv)
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
just typecheck-frontend       # svelte-check (regenerates API types first; needs uv)
just typecheck-backend        # ty type check
just types                    # regenerate frontend API types (auto: every consumer depends on it)
just seed                     # seed DB with sample data
just up                       # containerized prod stack
```
