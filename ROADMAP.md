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

## Milestone 2 — UX Polish ✅

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

- [x] **WL-2.6: Category Drill-Down Navigation** ✅

dev S · user med · 🟡

- [x] Replace flat two-level tree with folder-style drill-down (tap to enter subcategory, back button to go back)
- [x] Support arbitrary nesting depth
- [x] Mobile-friendly: one level visible at a time, full-width cards

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

- [ ] **WL-3.3: Tailwind Theme Tokens** 🚧

dev S · user med · 🟡

- [x] Replace hardcoded hex colours (`bg-[#1a1a2e]` etc.) with `@theme`
      tokens in `src/app.css` (`bark-*`, `ink-*`, `accent-*`, status scales);
      chart series colours centralised in `src/lib/theme.ts`. App stays
      dark-only for now — values unchanged.
- [ ] Add `dark:` variant support so light/dark both work
- [ ] Add theme toggle component (system / light / dark)
- [ ] Persist preference in `localStorage`

- [ ] **WL-3.4: Adopt a Headless Component Library** 🚧

dev M · user low · 🟡

- [x] Evaluate [Bits UI](https://bits-ui.com) (Svelte 5 runes-native, accessible) — chosen over Melt UI (lower-level) and styled kits (would change the look)
- [x] Migrate the hand-rolled `Select` to Bits UI `Select` (same `items`/`value`/`onchange` API; still iOS-safe via Floating UI + portal). −225 lines.
- [x] Migrate `Modal` to Bits UI `Dialog` (gains focus-trap + scroll-lock; same `open`/`title`/`onclose` API). −57 lines.
- [ ] Standardise other primitives as features land — Checkbox/AlertDialog (WL-4.1), Date Picker/Tooltip (WL-4.2), Tabs/Combobox (WL-5.1)
- [ ] Keep bundle impact in check — pilot added ~32 KB gz (Select + Dialog + Floating UI); marginal cost drops as more components reuse the core. Only import what's used.

- [x] **WL-3.5: UX Polish (round 2)** ✅

dev S · user med · 🟡

- [x] Analytics: when the restock modal contains an open `Select`, the first
      Escape should close only the dropdown (not the modal); Escape closes the
      modal only when the dropdown is already closed. Coordinate Esc handling
      between `Select` and `Modal`.
- [x] Scan on mobile: guard against missing `navigator.mediaDevices` /
      `getUserMedia` (undefined outside a secure context, which threw a bare
      TypeError). `BarcodeScanner` now shows an actionable message —
      `scanner.insecureContext` over HTTP ("open over HTTPS"),
      `scanner.cameraUnavailable` over HTTPS — instead of opening an empty
      modal. (The compose stack already serves HTTPS via nginx + mkcert with
      an openssl fallback in `40-setup-certs.sh`; the error only appeared via
      the Vite dev server's plain-HTTP LAN origin.)
- [x] Enable HTTPS for the Vite dev server: `just dev https` (or
      `just frontend https`) sets `DEV_HTTPS=true`, which serves over TLS using
      the mkcert certs in `certs/`, so camera scanning works on-device over the
      LAN. Falls back to a clear "run `just certs`" error if certs are missing.

---

## Milestone 4 — Core Loop: Use · Fill · Track ⬜

Goal: the everyday heart of the app — make adding, consuming, and correcting
stock effortless and mistake-proof. **Higher priority than the shopping list**:
using/filling/tracking is the product; the rest is add-ons.

- [ ] **WL-4.1: Manual Product Entry** ⬜

dev S · user critical · 🟢

- [ ] When Open Food Facts has no match, offer a "create it yourself" path instead of a dead end (store brands, bakery, loose produce)
- [ ] Manual name + optional brand / category / image; with or without an EAN
- [ ] Reuse the existing `POST /api/products` (no OFF data required) — this is mostly a frontend flow on the scan page
- [ ] Result is a normal trackable product (stock movements, chamber, analytics)

- [ ] **WL-4.2: Mistake Recovery** ⬜

dev M · user high · 🟢

- [ ] Undo last transaction — one tap from the scan success toast and from an activity view
- [ ] Activity / history view: recent `in`/`out` movements (global and per product)
- [ ] Edit / delete a transaction: `DELETE` + `PATCH /api/transactions/{id}`, stock recomputed
- [ ] Product delete (`DELETE /api/products/{id}`; block-with-reassign or cascade) + duplicate merge
- [ ] Unblocks the category-delete dead end (can't delete category while a product uses it, but products can't be deleted today)

- [ ] **WL-4.3: Quick Stock Adjust** ⬜

dev S · user high · 🟢

- [ ] `+`/`−` steppers on inventory rows → record `in`/`out` without re-scanning
- [ ] "Consume one" fast path ("I ate an apple" = one tap)

- [ ] **WL-4.4: Inventory Filtering** ⬜

dev XS · user med · 🟡

- [ ] Filter by category and by low-stock, combined with the existing fuzzy search

- [ ] **WL-4.5: Consistency Cleanup** 🚧

dev S · user med · 🟡
See `TODOS.md` for the concrete code deltas.

- [x] Unify "low stock" on the category restock thresholds (drop the hardcoded `stock <= 1` in inventory; chamber "Required" now counts items needing restock)
- [x] Finish modal standardisation — migrate the BarcodeScanner and chamber modals to the Bits UI `Modal`
- [ ] Colour-token cleanup (scan `gray-*` → `ink-*`; tokenise chamber gold) and i18n the leaked scan strings

---

## Milestone 5 — Playful Chamber & Gamification ⬜

Goal: turn tracking into play — the chamber reacts, items animate, kids earn
progress and real rewards. _Would a 10-year-old keep scanning for fun?_
Animations use [Lottie](https://lottiefiles.com/) (`lottie-web`) plus
AI-generated SVG/art driven by the design concept below.

- [ ] **WL-5.1: Profiles & Attribution** ⬜

dev S · user high · 🟢

- [ ] Lightweight profiles — *not* logins: pick a profile before scanning, like a Netflix/Switch user picker. The app stays fully usable with none selected.
- [ ] Profile switcher in the nav (next to `LocaleSwitcher`); active profile persisted in `localStorage` and sent with mutations — no server session
- [ ] Preset avatars to start (pick a character + colour), stored as a layered-SVG config so a buildable avatar + unlockable equipment can grow on top later (WL-5.4)
- [ ] Level derived from XP (don't store level separately)
- [ ] Foundation for all per-profile gamification (XP, streaks, leaderboard) and the later co-op/PvP modes (WL-9.2)

Data model:

```
Profile
  id, name, avatar_config (JSON: layered SVG part ids),
  xp (int, source of truth — level = f(xp)),
  current_streak, longest_streak, last_active_on (date | null),
  locale (str | null), is_archived (bool), created_at

ProfileAchievement   id, profile_id FK, achievement_key, earned_at    # unique(profile_id, key)
ProfileUnlock        id, profile_id FK, item_key, acquired_at         # owned cosmetics/equipment; unique(profile_id, item_key)

InventoryTransaction.profile_id   FK -> Profile, nullable, indexed     # NULL = no profile selected / legacy
```

- [ ] **WL-5.2: Tap-to-Consume Chamber Interaction** ⬜

dev S · user high · 🟢

- [ ] Tap an item/pile in the chamber to consume one → records an `out`, with a satisfying vanish (poof of crumbs/dust)
- [ ] Add-to-chamber animation: a scanned item arcs and bounces into its pile
- [ ] Doubles as the "quick consume" UX (complements WL-4.3) and the chamber's reason to exist

- [ ] **WL-5.3: Progression — XP, Levels & the Living Chamber** ⬜

dev M · user high · 🟢
Depends: WL-5.1 (profiles)

- [ ] Foundational events/XP store (one primitive that all gamification reads from); XP accrues to the active profile
- [ ] Earn XP for scans, restocks, and consuming-before-expiry; level up
- [ ] The chamber visibly levels up with you (torches light, shelves fill, background grows richer — see design concept)
- [ ] Guardian mood: thrives when stocked, looks forlorn/cobwebbed when bare (formalises today's 🏚️ empty state)

- [ ] **WL-5.4: Achievements, Streaks & Rewards** ⬜

dev M · user high · 🟢
Depends: WL-5.3 · leaderboard depends on WL-9.2

- [ ] Badges: First Scan, 50 Stocked, Cleared the List, **Zero-Waste Week** (nothing expired) — real-world value + teaches kids
- [ ] Daily streak with a growing flame; combo meter for rapid multi-scan after a shop
- [ ] Configurable real-life rewards per tier ("Level 5 → pick movie night")
- [ ] Achievements / levels unlock avatar equipment (`ProfileUnlock`) — the reason to keep earning
- [ ] "Pantry-dex": a collectible card per product scanned (gotta scan 'em all)
- [ ] Leaderboard / "Scanner of the Week" once multi-user lands (WL-9.2)

- [ ] **WL-5.5: Animation & Art Pipeline (Lottie + AI assets)** ⬜

dev M · user med · 🟡

- [ ] Adopt Lottie (`lottie-web`, thin Svelte wrapper) for celebratory + ambient animations; respect `prefers-reduced-motion`
- [ ] Use the **UI Design Concept** below as image-generation prompts → SVG art and Lottie animations
- [ ] Optional sound effects (scan chime, consume crunch, level-up fanfare) — off by default, kid-delight toggle

### UI Design Concept (prompt library for image/animation generation)

Art direction: warm, storybook flat-vector; earthy browns with gold accents
(matches the `bark-*` / `ink-*` / gold tokens); dark-friendly; simple shapes
that export cleanly to SVG; transparent backgrounds for sprites; no text in
images. Feed these as prompts to an image/Lottie generator, then tokenise
colours to the theme.

- **Chamber scene (background, per level).** "A cozy underground stone pantry
  and treasure chamber, warm torchlight, wooden shelves along the walls, stone
  floor, soft golden glow, painterly storybook style, flat front-on view, empty
  central floor where grocery items pile up, muted earthy browns with gold
  accents, no text, 3:2." Level variants: L1 bare with one torch → L5 many lit
  torches, full shelves, banners, richer detail.
- **Guardian mascot.** "A friendly pantry guardian — a small round creature
  made of grains/bread, big expressive eyes, storybook flat-vector, centered,
  transparent background." States: happy (stocked), neutral, sleepy/sad (bare).
- **Item tokens.** Optional custom flat-vector food icons matching the palette,
  as a richer alternative to emoji (keep emoji fallback).
- **Achievement badges.** "Circular medal with ribbon, bronze/silver/gold
  tiers, flat-vector, gold palette, transparent background" — one frame, recolor
  per tier.
- **Animations (Lottie).** Level-up: "golden sparkle burst, a shelf/torch
  igniting, ~1.2s ease-out." Consume: "item shrinks into a small dust/crumb
  poof, ~0.4s." Add-to-chamber: "item arcs in from the top, lands with a bounce
  and a dust puff." Streak flame: "looping warm flame that grows taller with
  streak length." Achievement unlock: "medal stamps in with a shine sweep."

---

## Milestone 6 — Robustness & Trust ⬜

Goal: the add-ons that make the core dependable on a Pi.

- [ ] **WL-6.1: Data Export / Backup** ⬜

dev S · user med · 🟡

- [ ] Export inventory + transactions + categories to CSV/JSON; import to restore
- [ ] Guards against SD-card loss (SQLite on a Pi has no backup today)

- [ ] **WL-6.2: PWA Install + Offline Scan Queue** ⬜

dev M · user med · 🟢

- [ ] Make the existing manifest installable; service worker for offline shell
- [ ] Queue scans/movements while offline, sync when back online (scan in the garage on bad wifi)

- [ ] **WL-6.3: Performance Pass** ⬜

dev S · user med · 🟡

- [ ] Chamber renders up to ~10 DOM nodes per product — cap/virtualise for large pantries
- [ ] Remove redundant full-list refetches (scan save calls `products.list()` repeatedly; several pages refetch on every change)

- [ ] **WL-6.4: Accessibility & Legibility** ⬜

dev S · user med · 🟡

- [ ] Contrast audit of the dark theme; larger tap targets for small hands; screen-reader labels (chamber decorative emojis, stat tables)

- [ ] **WL-6.5: Interactive Test Coverage** ⬜

dev S · user — · ⚪

- [ ] Component/integration tests for the scan flow and `Select`/`Modal` (the most-used, most-regressed paths) — completes the WL-3.2 leftover (needs a DOM testing library)

- [ ] **WL-6.6: Onboarding / First-Run** ⬜

dev S · user med · 🟡

- [ ] Guided "scan your first item" beat from the empty chamber (doubles as the first achievement)

---

## Milestone 7 — Smart Shopping List ⬜

Goal: auto-generate a shopping list from low-stock items; check off while shopping.

- [ ] **WL-7.1: Shopping List** ⬜

dev M · user high · 🟢

- [ ] Auto-populate from existing restock data: category-level `restock_target`/`restock_min` with inheritance already drives `/api/analytics/restock-overview` — shopping list consumes that endpoint
- [ ] Optional per-product threshold override (extends, not replaces, category-level thresholds)
- [ ] Manual additions for one-off items (free-text, not tied to a product)
- [ ] Check-off items during a shopping trip → auto-record `in` transaction with quantity
- [ ] Shareable list (household members see the same list in real time)
- [ ] Clear completed items / archive past trips

- [ ] **WL-7.2: Expiry Date Tracking** ⬜

dev M · user high · 🟢

- [ ] Optional expiry date field on stock-in transactions
- [ ] "Expiring soon" badge on inventory items
- [ ] Sort/filter inventory by expiry
- [ ] Push notification (PWA) for items expiring within N days
- [ ] Feeds the Zero-Waste gamification (WL-5.4)

---

## Milestone 8 — Recipe Engine ⬜

Goal: match current stock against a personal recipe database; answer "what can I cook tonight?"

- [ ] **WL-8.1: Recipe Database** ⬜

dev M · user high · 🟢

- [ ] [Cooklang](https://cooklang.org/) format for recipes (plain-text, git-friendly, ingredient-aware)
- [ ] Import/manage `.cook` files via the UI
- [ ] Parse Cooklang → structured ingredient list with quantities and units
- [ ] Recipe browser with search and category/tag filters

- [ ] **WL-8.2: Stock-Aware Recipe Matching** ⬜

dev M · user critical · 🟢
Depends: WL-8.1

- [ ] Match recipe ingredients against current inventory (fuzzy name matching + unit normalisation)
- [ ] Three tiers: "ready to cook" (all ingredients in stock), "almost ready" (1–2 items missing), "need shopping"
- [ ] Missing-ingredient delta → one-tap add to shopping list (WL-7.1)
- [ ] "Cook this" action → bulk-deduct ingredients from inventory

- [ ] **WL-8.3: AI Recipe Suggestions** ⬜

dev M · user high · 🟡

- [ ] On-device or local-network LLM (e.g. Ollama) suggests meals from available ingredients
- [ ] Substitution suggestions for missing ingredients
- [ ] Generate new Cooklang recipes inspired by the user's cooking history and current stock
- [ ] Privacy-first: no data leaves the home network
- [ ] Graceful fallback when no LLM is available (feature simply hidden)

---

## Milestone 9 — Stretch Goals ⬜

- [ ] **WL-9.1: Receipt Scanning** ⬜

dev L · user med · 🟡

- [ ] OCR receipt scanning to auto-record multiple items
- [ ] Price extraction and category inference

- [ ] **WL-9.2: Accounts, Household Sync & Game Modes** ⬜

dev L · user med · 🟡
Depends: WL-5.1 (profiles)

- [ ] Real accounts / lightweight auth (PIN or household code) layered on top of the existing profiles
- [ ] Cross-device household sync (shared inventory + profiles in real time)
- [ ] Co-op vs the chamber monster / PvP game modes (design TBD) on the profiles + XP foundation
- [ ] Unlocks the gamification leaderboard / "Scanner of the Week" (WL-5.4)
