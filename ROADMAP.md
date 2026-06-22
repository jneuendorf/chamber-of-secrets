# Chamber of Secrets — Roadmap

Tracks delivery status. Each work-list item (WL-X.Y) carries a checkbox.

Legend: ✅ done · 🚧 in progress · ⬜ not started

### Cost–benefit key

- **dev** (effort): XS (hours) · S (days) · M (1–2 wk)
- **user** (impact): low · med · high · critical
- **ROI**: 🟢 high · 🟡 med · 🔴 low · ⚪ foundational

---

## Milestone 0 — Backend & Data Layer ✅

Goal: FastAPI backend, SQLAlchemy models, Alembic migrations, EAN lookup.

- [x] **WL-0.1: Project Scaffold** ✅

dev S · user — · ⚪

  - [x] FastAPI app with lifespan, CORS, auto-migrate on startup
  - [x] SQLAlchemy 2 models (Product, InventoryTransaction, ProductRevision, Category)
  - [x] Alembic migrations with batch mode for SQLite
  - [x] Pydantic settings (`APP_*` env vars)

- [x] **WL-0.2: EAN Lookup Service** ✅

dev S · user high · 🟢

  - [x] Open Food Facts API integration (cache-first)
  - [x] Auto-create product on first scan
  - [x] Product refresh with immutable revision snapshot

- [x] **WL-0.3: CRUD Routers** ✅

dev S · user high · 🟢

  - [x] Products router (list, lookup, refresh)
  - [x] Transactions router (list, create)
  - [x] Categories router (list, create, update, delete)
  - [x] Analytics router (spending by category with date range)

- [x] **WL-0.4: Test Fixtures & Seed Data** ✅

dev XS · user — · ⚪

  - [x] Food catalog JSON fixture
  - [x] Seed script with confirmation prompt
  - [x] Backend unit tests

---

## Milestone 1 — Frontend Shell & Core UI ✅

Goal: SvelteKit app with scanning, inventory, analytics, i18n.

- [x] **WL-1.1: App Scaffold** ✅

dev M · user high · 🟢

  - [x] SvelteKit 2 + Svelte 5 + TypeScript + Tailwind CSS 4
  - [x] Typed API client (`lib/api/client.ts`)
  - [x] Mobile-friendly nav bar
  - [x] Dark colour scheme (proper theming deferred to WL-3.3)
  - [x] Docker + nginx with TLS (mkcert), Podman support

- [x] **WL-1.2: Barcode Scanner** ✅

dev M · user critical · 🟢

  - [x] Camera-based barcode scanning (`@undecaf/barcode-detector-polyfill`)
  - [x] Live video preview during scanning
  - [x] Product lookup on scan → stock movement form
  - [x] Stock validation and positive quantity check

- [x] **WL-1.3: Inventory Page** ✅

dev S · user high · 🟢

  - [x] Product list with computed stock levels
  - [x] Fuzzy search (Fuse.js)

- [x] **WL-1.4: Analytics Page** ✅

dev S · user med · 🟡

  - [x] Spending by category (Chart.js bar + pie charts)
  - [x] Date-range picker
  - [x] Parent-category aggregation

- [x] **WL-1.5: Categories Page** ✅

dev S · user med · 🟡

  - [x] Category list with emoji icons
  - [x] Category picker component for scan page
  - [x] Hierarchical parent/child display

- [x] **WL-1.6: Internationalisation** ✅

dev S · user med · 🟡

  - [x] svelte-i18n v4 (EN + DE)
  - [x] Locale switcher in nav bar
  - [x] All user-facing strings extracted to locale JSON

- [x] **WL-1.7: Chamber Visualisation** ✅

dev S · user low · 🔴

  - [x] Chamber page with visual stock pile rendering

---

## Milestone 2 — UX Polish 🚧

Goal: fix rough edges, improve scanning flow, categories UX.

- [x] **WL-2.1: Scan Flow Improvements** ✅

dev S · user high · 🟢

  - [x] Re-activate barcode scanner immediately after recording a transaction
  - [x] Prompt category selection directly after scanning
  - [x] Reset quantity field to 1 after each scan

- [x] **WL-2.2: Category Management** ✅

dev S · user med · 🟡

  - [x] Manual category creation from the management page
  - [x] Category deletion (with `confirm()` prompt)
  - [x] Emoji fallback: child inherits from parent if not set

- [x] **WL-2.3: Inventory Enhancements** ✅

dev M · user med · 🟡

  - [x] Manually add an image to an inventory item (camera capture)
  - [x] Fix chamber selection behaviour (disable marking)

- [x] **WL-2.4: Analytics Fixes** ✅

dev S · user med · 🟡

  - [x] Fix translation bug: English strings shown despite German selected
  - [x] Improve parent/child aggregation in pie chart (avoid double-counting)
  - [x] Replace static pie charts with interactive drill-down donut (iOS-style slide navigation)
  - [x] Extract analytics utils into testable module with 23 tests

- [x] **WL-2.5: UX Polish** ✅

dev XS · user med · 🟡

  - [x] Replace browser `confirm()` with styled modal dialog component
  - [x] Use for category deletion and other destructive actions
  - [x] Image upload: standard file picker as primary, small camera shortcut via `capture="environment"` on mobile

- [ ] **WL-2.6: Category Drill-Down Navigation** ⬜

dev S · user med · 🟡

  - [ ] Replace flat two-level tree with folder-style drill-down (tap to enter subcategory, breadcrumb to go back)
  - [ ] Support arbitrary nesting depth
  - [ ] Mobile-friendly: one level visible at a time, full-width cards

---

## Milestone 3 — Tooling & Quality 🚧

Goal: code quality tooling, formatting, linting, test infrastructure.

- [x] **WL-3.1: Biome Setup** ✅

dev XS · user — · ⚪

  - [x] Replace Prettier with Biome 2.x (lint + format)
  - [x] Biome config matching project conventions (4-space indent, single quotes, semicolons asNeeded)
  - [x] Update justfile recipes
  - [x] VS Code extension recommendation

- [x] **WL-3.2: Frontend Test Infrastructure** ✅

dev S · user — · ⚪

  - [x] Configure `bun test` for unit tests (`@types/bun` for type-safe test authoring)
  - [x] Add `test` / `test:coverage` scripts to `package.json`, `just test-frontend` and `just test` (all) recipes
  - [x] Add `just check` meta-recipe (lint + typecheck + test, both layers)
  - [x] Seed initial tests: API client (16 tests), scan utils (16 tests), i18n key sync (3 tests)
  - [x] Wire coverage reporting (`bun test --coverage`); tested modules at 100%
  - [ ] Component-level tests (requires DOM testing library — future work)

- [ ] **WL-3.3: Tailwind Theme Tokens** ⬜

dev S · user med · 🟡

  - [ ] Replace hardcoded hex colours (`bg-[#1a1a2e]` etc.) with Tailwind CSS v4 theme variables / `@theme` directive
  - [ ] Add `dark:` variant support so light/dark both work
  - [ ] Add theme toggle component (system / light / dark)
  - [ ] Persist preference in `localStorage`

---

## Milestone 4 — Smart Shopping List ⬜

Goal: auto-generate a shopping list from low-stock items; check off while shopping.

- [ ] **WL-4.1: Shopping List** ⬜

dev M · user high · 🟢

  - [ ] Auto-populate from existing restock data: category-level `restock_target`/`restock_min` with inheritance already drives `/api/analytics/restock-overview` — shopping list consumes that endpoint
  - [ ] Optional per-product threshold override (extends, not replaces, category-level thresholds)
  - [ ] Manual additions for one-off items (free-text, not tied to a product)
  - [ ] Check-off items during a shopping trip → auto-record `in` transaction with quantity
  - [ ] Shareable list (household members see the same list in real time)
  - [ ] Clear completed items / archive past trips

- [ ] **WL-4.2: Expiry Date Tracking** ⬜

dev M · user high · 🟢

  - [ ] Optional expiry date field on stock-in transactions
  - [ ] "Expiring soon" badge on inventory items
  - [ ] Sort/filter inventory by expiry
  - [ ] Push notification (PWA) for items expiring within N days

---

## Milestone 5 — Recipe Engine ⬜

Goal: match current stock against a personal recipe database; answer "what can I cook tonight?"

- [ ] **WL-5.1: Recipe Database** ⬜

dev M · user high · 🟢

  - [ ] [Cooklang](https://cooklang.org/) format for recipes (plain-text, git-friendly, ingredient-aware)
  - [ ] Import/manage `.cook` files via the UI
  - [ ] Parse Cooklang → structured ingredient list with quantities and units
  - [ ] Recipe browser with search and category/tag filters

- [ ] **WL-5.2: Stock-Aware Recipe Matching** ⬜

dev M · user critical · 🟢
Depends: WL-5.1

  - [ ] Match recipe ingredients against current inventory (fuzzy name matching + unit normalisation)
  - [ ] Three tiers: "ready to cook" (all ingredients in stock), "almost ready" (1–2 items missing), "need shopping"
  - [ ] Missing-ingredient delta → one-tap add to shopping list (WL-4.1)
  - [ ] "Cook this" action → bulk-deduct ingredients from inventory

- [ ] **WL-5.3: AI Recipe Suggestions** ⬜

dev M · user high · 🟡

  - [ ] On-device or local-network LLM (e.g. Ollama) suggests meals from available ingredients
  - [ ] Substitution suggestions for missing ingredients
  - [ ] Generate new Cooklang recipes inspired by the user's cooking history and current stock
  - [ ] Privacy-first: no data leaves the home network
  - [ ] Graceful fallback when no LLM is available (feature simply hidden)

---

## Milestone 6 — Stretch Goals ⬜

- [ ] **WL-6.1: Receipt Scanning** ⬜

dev L · user med · 🟡

  - [ ] OCR receipt scanning to auto-record multiple items
  - [ ] Price extraction and category inference

- [ ] **WL-6.2: Multi-User / Household** ⬜

dev L · user med · 🟡

  - [ ] User accounts and lightweight authentication (PIN or household code)
  - [ ] Shared household inventory
  - [ ] Per-user transaction attribution and personal shopping lists

- [ ] **WL-6.3: Gamification** ⬜

dev S · user high · 🟢

  - [ ] Scan streaks, badges, leaderboard for household members
  - [ ] "Scan of the week" highlights
  - [ ] Makes the app fun for kids — core principle compliance
