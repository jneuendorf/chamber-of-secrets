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
- [x] Dark color scheme (light theme + toggle added in WL-3.3)
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

- [x] **WL-1.6: Internationalization** ✅

dev S · user med · 🟡

- [x] svelte-i18n v4 (EN + DE)
- [x] Locale switcher in nav bar
- [x] All user-facing strings extracted to locale JSON

- [x] **WL-1.7: Chamber Visualization** ✅

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
- [x] Fix chamber selection behavior (disable marking)

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

## Milestone 3 — Tooling & Quality ✅

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
- Moved out: component-level tests need a DOM testing library — owned by WL-6.5

- [x] **WL-3.3: Tailwind Theme Tokens** ✅

dev S · user med · 🟡

- [x] Replace hardcoded hex colors (`bg-[#1a1a2e]` etc.) with `@theme`
      tokens in `src/app.css` (`bark-*`, `ink-*`, `accent-*`, status scales);
      chart series colors centralized in `src/lib/theme.ts`.
- [x] Light/dark support — not via `dark:` variants (that would touch every
      class in every component) but by making each token a
      `light-dark(<light>, <dark>)` pair, so components stay untouched and a
      theme is retuned in one file. Step numbers are roles, not lightness.
      Also defined five tokens components already used but `@theme` lacked
      (`bark-500`, `accent-700`/`300`, `danger-100`, `success-200`)
- [x] Theme toggle (`ThemeSwitcher.svelte`, nav bar): one button cycling
      system → light → dark. Sets `data-theme` → `color-scheme` on <html>;
      the nav, the chamber scene and the celebration toast pin
      `color-scheme: dark`
- [x] Persist preference in `localStorage`, applied by an inline script in
      `app.html` before first paint. Charts resolve tokens through
      `themeColor(token, scheme)` and redraw on a theme change

- [x] **WL-3.4: Adopt a Headless Component Library** ✅

dev M · user low · 🟡

- [x] Evaluate [Bits UI](https://bits-ui.com) (Svelte 5 runes-native, accessible) — chosen over Melt UI (lower-level) and styled kits (would change the look)
- [x] Migrate the hand-rolled `Select` to Bits UI `Select` (same `items`/`value`/`onchange` API; still iOS-safe via Floating UI + portal). −225 lines.
- [x] Migrate `Modal` to Bits UI `Dialog` (gains focus-trap + scroll-lock; same `open`/`title`/`onclose` API). −57 lines.
- Standing rule, not a task (see `AGENTS.md` → Headless UI): adopt a further
  primitive only where a native element can't do the job, and only import what's
  used — the pilot cost ~32 KB gz (Select + Dialog + Floating UI), later primitives
  reuse that core. So far native has always sufficed: `<input type="date">` for
  the analytics range, checkboxes for the OFF opt-in and restock-inherit, a plain
  cycling button for the WL-3.3 theme toggle
- Candidates are decided by the item that needs them: Switch → WL-6.7
  (handedness; likely a plain button too), Tooltip → WL-6.6 (onboarding),
  AlertDialog → WL-6.4

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

## Milestone 4 — Core Loop: Use · Fill · Track 🚧

Goal: the everyday heart of the app — make adding, consuming, and correcting
stock effortless and mistake-proof. **Higher priority than the shopping list**:
using/filling/tracking is the product; the rest is add-ons.

- [x] **WL-4.1: Manual Product Entry** ✅

dev S · user critical · 🟢

- [x] When Open Food Facts has no match, offer a "create it yourself" path instead of a dead end (store brands, bakery, loose produce)
- [x] Manual name + optional brand / category / image; with or without an EAN
- [x] Reuse the existing `POST /api/products` (no OFF data required) — this is mostly a frontend flow on the scan page
- [x] Result is a normal trackable product (stock movements, chamber, analytics)

- [x] **WL-4.2: Mistake Recovery** ✅

dev M · user high · 🟢

- [x] Undo last transaction — one tap from the scan success toast (5s window); also editable/deletable from the activity view
- [x] Activity / history view: recent `in`/`out` movements (global and per product via a product filter)
- [x] Edit / delete a transaction: `DELETE` + `PATCH /api/transactions/{id}`, stock recomputed (derived at query time)
- [x] Product delete (`DELETE /api/products/{id}`, cascade transactions + revisions + image) + duplicate merge (`POST /api/products/merge` repoints transactions onto the survivor)
- [x] Unblocks the category-delete dead end (products can now be deleted, freeing their category)

- [x] **WL-4.3: Quick Stock Adjust** ✅

dev S · user high · 🟢

- [x] `+`/`−` steppers on inventory rows → record `in`/`out` without re-scanning
- [x] "Consume one" fast path ("I ate an apple" = one tap)

- [x] **WL-4.4: Inventory Filtering** ✅

dev XS · user med · 🟡

- [x] Filter by category and by low-stock, combined with the existing fuzzy search

- [x] **WL-4.5: Consistency Cleanup** ✅

dev S · user med · 🟡
See `TODOS.md` for the concrete code deltas.

- [x] Unify "low stock" on the category restock thresholds (drop the hardcoded `stock <= 1` in inventory; chamber "Required" now counts items needing restock)
- [x] Finish modal standardization — migrate the BarcodeScanner and chamber modals to the Bits UI `Modal`
- [x] Color-token cleanup (scan `gray-*` → `ink-*`; tokenize chamber gold) and i18n the leaked scan strings

- [x] **WL-4.6: Contribute Back to Open Food Facts** ✅

dev M · user med · 🟢
Depends: WL-4.1 (manual entry). Achievement hook: WL-5.4.

- [x] When a real scanned EAN misses OFF and the user creates it manually, offer an opt-in "add it to Open Food Facts too" step — turns the dead end into a prosocial contribution
- [x] Barcode-only: OFF is barcode-keyed, so no-EAN manual products (bakery, loose produce) are excluded from submission
- [x] Write via the OFF product API (`POST /cgi/product_jqm2.pl`): `code`, `product_name`, `brands`, `categories`, `lc`
- [x] Single app-registered OFF account + descriptive `User-Agent`; secrets server-side (submission proxied through the backend, not the browser)
- [x] Guard the shared DB: name required (`ProductCreate.name`), explicit opt-in checkbox, never auto-submit; contributions are ODbL open data
- [x] Dev/tests hit the staging instance (`world.openfoodfacts.net`, basic auth `off`/`off`) — never pollute prod (defaults in `config.py`; prod overrides via `APP_OFF_*`)
- [x] Unlocks the **"Explorer"** achievement — "you put a new product on the world map". Granted in `routers/products.py` when `?profile_id=` is passed; the badge itself is catalogued with the rest in WL-5.4
- Dormant, not missing: front image via `/cgi/product_image_upload.pl` is fully wired (`contribute_image` + local-upload reader) but sits behind `off_contribute_images` (default off). Flip the flag once the manual scan flow captures a photo — no code change needed

---

## Milestone 5 — Playful Chamber & Gamification 🚧

Goal: turn tracking into play — the chamber reacts, items animate, kids earn
progress and real rewards. _Would a 10-year-old keep scanning for fun?_
Animations use [Lottie](https://lottiefiles.com/) (`lottie-web`) plus
AI-generated SVG/art driven by the design concept below.

- [x] **WL-5.1: Profiles & Attribution** ✅

dev S · user high · 🟢

- [x] Lightweight profiles — _not_ logins: pick a profile before scanning, like a Netflix/Switch user picker. The app stays fully usable with none selected.
- [x] Profile switcher in the nav (next to `LocaleSwitcher`); active profile persisted in `localStorage` and sent with mutations — no server session
- [x] Preset avatars to start (pick a character + color), stored as a layered-SVG config so a buildable avatar + unlockable equipment can grow on top later (WL-5.4). `avatar_config.base` holds a **stable part id** (`"fox"`), never a glyph or SVG markup — the id decouples data from art, so parts can be redrawn or swapped from emoji to SVG without touching stored profiles. The emoji are a stand-in renderer; the SVG parts, the `layers` key, and the compositor land with WL-5.4 (additive on a JSON column — no migration)
- [x] Level derived from XP (`level_for_xp`, don't store level separately)
- [x] Foundation for all per-profile gamification (XP, streaks, leaderboard) and the later co-op/PvP modes (WL-9.2)

Data model (as built): `Profile` table + nullable indexed
`InventoryTransaction.profile_id`. The `ProfileAchievement` / `ProfileUnlock`
tables below landed only once code read them — `ProfileAchievement` with WL-5.4,
`ProfileUnlock` still waiting on the avatar compositor.

```
Profile
  id, name, avatar_config (JSON: layered SVG part ids — {base, color} today;
                           `layers: [{slot, part}]` added by WL-5.4),
  xp (int, source of truth — level = f(xp)),
  current_streak, longest_streak, last_active_on (date | null),
  locale (str | null), is_archived (bool), created_at

InventoryTransaction.profile_id   FK -> Profile, nullable, indexed     # NULL = no profile selected / legacy

ProfileAchievement   id, profile_id FK, achievement_key, earned_at    # unique(profile_id, key) — WL-5.4

# Still deferred:
ProfileUnlock        id, profile_id FK, item_key, acquired_at         # owned cosmetics/equipment; unique(profile_id, item_key)
```

- [x] **WL-5.2: Tap-to-Consume Chamber Interaction** ✅

dev S · user high · 🟢

- [x] Tap an item in the chamber to consume it → records an `out`, with a satisfying vanish (scale+fade+spin poof). A confirm/chooser sheet names the product first (emoji are lossy — same 🥛 can mean several products) and carries a quantity stepper (consume more than one at a time). A 5s undo toast (with an explicit ✕ dismiss) reverses accidental taps by deleting the transaction; a new consume replaces the toast (undo targets the latest action).
- [x] The **tapped** dot is the exact one that poofs — a `consumed`-slots overlay excludes the touched slot so no unrelated dot vanishes, and a big (capped) pile refills from its reserve instead of gapping.
- [x] Doubles as the "quick consume" UX (complements WL-4.3) and the chamber's reason to exist
- [x] Add-to-chamber animation: a dot that joins its pile arcs in from above and bounces into its slot (`in:arrive`, path in the pure, tested `arcIn()` in `$lib/utils/chamber.ts`; respects `prefers-reduced-motion`). Within the page that's an undo returning a consumed dot — nothing else adds stock on `/chamber`, scans arriving from `/scan` feed the same transition (WL-5.6). A per-product `pileTrend` keeps a capped pile's reserve swap silent: a consume poofs the tapped dot without a refill flying in, an undo arcs it back without the reserve dot poofing. Local transitions skip the first render, so a page load doesn't rain items
- Deferred behind seams (see WL-5.6 for cross-route): crumb/dust particles → WL-5.5 art pass; dense-pile chooser widening (fill the sheet with overlapping dots) → when tap collisions actually bite; pile/stack glyph rendering mode
- Foundation shipped: `$lib/utils/chamber.ts` (pure, tested layout — stable per-`(product, slot)` dot keys, `visibleSlots` overlay so the tapped dot is the one removed and one consume never reflows other piles) + `ConsumeSheet.svelte` (candidate list: 1 = confirm, N = chooser; per-item quantity). Depleted products now show zero dots instead of a gray ghost. `scrollbar-gutter: stable` keeps the modal from shifting the page.

- [x] **WL-5.3: Progression — XP, Levels & the Living Chamber** ✅

dev M · user high · 🟢
Depends: WL-5.1 (profiles)

- [x] Foundational events/XP store: `services/progression.py` is the single award point (backend), `$lib/progression.ts` the single store every gamification feature reads (frontend). XP accrues to the active profile on every attributed movement; unattributed movements award nothing
- [x] Earn XP for scans/restocks (`in`, 10) and consuming (`out`, 2); level derived via `level_for_xp`, level-up announced app-wide (WL-5.7). Daily streak rolls with it (consecutive day extends, gap restarts, longest kept)
- [x] The chamber visibly levels up with you — `chamberStage(level)` (1–5) rendered as `data-stage` on the scene, driving a placeholder brightness ramp. Torches/shelves/background art hangs off the same hook in WL-5.5
- [x] Guardian mood: `guardianMood()` derives `thriving`/`content`/`sparse`/`forlorn` from the share of products needing restock, rendered as `data-mood` + a stand-in glyph. Real art (cobwebs, animation) in WL-5.5
- XP is deliberately not reversed on undo (WL-5.2) — cheaper than an award ledger; revisit only if XP ever buys something scarce
- Moved out: the consuming-**before-expiry** XP bonus needs batch expiry dates — owned by WL-7.2, lands there

- [ ] **WL-5.4: Achievements, Streaks & Rewards** 🚧

dev M · user high · 🟢
Depends: WL-5.3 · leaderboard depends on WL-9.2

- [x] Badges: `services/achievements.py` grants them from data that already exists — First Scan, Well Stocked (50 `in`), Week Streak, Chamber Keeper (level 5), **Explorer** (added a product to Open Food Facts, WL-4.6). Stored as keys in `profile_achievements`; names and art are client-side, so a badge is renamed or redrawn without a migration. Earned badges are diffed on profile refresh and announced app-wide (WL-5.7)
- [x] Dedicated per-profile progress page (`/profile/[id]`, reached from the picker): avatar, level + XP-to-next bar, streak, and the full badge grid (earned + locked). Standalone route, so a later nav redesign can reposition it
- [x] Daily streak with a growing flame — `StreakFlame.svelte` (stand-in 🔥, size from the pure, tested `flameScale()`: grows fast over the first days, caps at 2× from a month on; flickers unless `prefers-reduced-motion`) on the profile page and the chamber ledger. The Lottie flame (WL-5.5) hangs off `data-streak`
- [x] Combo meter for rapid multi-scan after a shop — on `/scan`, each stock-in within 90s of the last extends the combo (`extendCombo()`, pure and tested); from ×2 a "⚡ Combo ×N" pill with a draining bar shows. Display only: no XP bonus, undo doesn't shrink it, out-scans leave it alone
- [x] Configurable real-life rewards per tier ("Level 5 → pick movie night") — household-wide `reward_tiers` (level + text); whoever reaches the level unlocks it. Configured and viewed on the profile page (add/remove, unlocked vs locked per profile). **Redeeming is per profile** (`profile_rewards`): mark/un-mark "✓ Redeemed" on your own active-profile page only (login-less UX guard — backend validates the reward is unlocked but can't enforce whose tap it is); others see a read-only redeemed tag. Idempotent, reversible, cascades on tier delete. The level-up "reward unlocked!" toast is its own item — WL-5.7
- [ ] **Avatar compositor** — render `avatar_config.layers: [{slot, part}]` over the base part, replacing today's emoji stand-in with real SVG. WL-5.1, `FEATURES.md` §2.9 and `schemas.py` all name WL-5.4 as its owner, so it belongs here. Additive on a JSON column — no migration. The art itself comes from WL-5.5
- [ ] Achievements / levels unlock avatar equipment (`ProfileUnlock`) — what the compositor renders, and the reason to keep earning
- [x] "Pantry-dex": a collectible card per product, per profile (gotta scan 'em all) — `GET /profiles/{id}/pantry-dex` derives the collection from the profile's attributed `in` movements (first-collected time + times stocked; nothing stored). Shown on the profile page: every household product in fixed order, collected cards with photo/icon + name, uncollected as "???" silhouettes. Card art (frames, rarity) is WL-5.5
- [ ] Leaderboard / "Scanner of the Week" once multi-user lands (WL-9.2)
- Deferred: the **"Cleared the List"** badge needs a shopping list — owned by WL-7.1, lands there
- Deferred: the **Zero-Waste Week** badge (nothing expired) needs expiry dates — owned by WL-7.2, lands there

- [ ] **WL-5.5: Animation & Art Pipeline (Lottie + AI assets)** ⬜

dev M · user med · 🟡

- [ ] Adopt Lottie (`lottie-web`, thin Svelte wrapper) for celebratory + ambient animations; respect `prefers-reduced-motion`
- [ ] Use the **UI Design Concept** below as image-generation prompts → SVG art and Lottie animations
- [ ] Optional sound effects (scan chime, consume crunch, level-up fanfare) — off by default, kid-delight toggle
- Seams already reserved by WL-5.3: `data-stage` (1–5) and `data-mood` on the chamber scene, plus `GUARDIAN_GLYPH` — the progression logic is design-agnostic, so the art pass is CSS/assets only

- [x] **WL-5.6: Cross-route "flying item" hand-off** ✅

dev S · user med · 🟡
Depends: WL-5.2

- [x] Scan on `/scan` → the just-added item arcs into its pile when you next open `/chamber`. `/scan` queues each stock-in in `$lib/arrivals.ts` (keyed by transaction id, so its undo withdraws it); `/chamber` drains the queue on load, holds the new dots back via the `consumed` overlay (`arrivalSlots()`, pure and tested), and releases them after the initial piles have landed — the WL-5.2 `in:arrive` transition does the rest
- The arc starts above the pile, not literally at the nav — a true across-the-nav flight needs SvelteKit view transitions; revisit with the WL-5.5 art pass if the plain arc doesn't sell it
- Inventory `+` doesn't queue arrivals (spec names `/scan`); a full reload drops the in-memory queue, so items just appear at rest

- [x] **WL-5.7: Level-Up & Reward Notifications** ✅

dev S · user high · 🟢
Depends: WL-5.3 (level-up event), WL-5.4 (`reward_tiers`)

- [x] Celebratory notification when a profile levels up — `Celebration.svelte`
      mounted in the root layout, so it fires on every route. This also fixed the
      reason it mattered: `/scan` and the inventory ± buttons awarded XP but never
      called `refreshProfile()`, so those levels went unnoticed until the next
      chamber visit
- [x] **"Reward unlocked!" callout** when the new level crosses a `reward_tiers`
      threshold (moved from WL-5.4) — names the real-life reward ("Level 5 → pick
      movie night"). Tiers are fetched at the crossing rather than held in a store
- [x] Fire **exactly once per crossing** — `levelUp` now carries `{ from, to }`
      instead of just the new level, so `rewardsUnlockedBetween()` can pick up
      every tier in a multi-level jump. The store holds a *transition*, cleared as
      soon as it's shown, which is the guard: the next refetch sees an unchanged
      level and stays quiet. `progressSince()` only diffs a profile against
      itself, so switching the picker to someone further along announces
      nothing. The `level >= tier.level` display derivation is untouched
- Announcements from one movement queue and play in turn — this retired the
      WL-5.3 limitation where simultaneous badges announced only the first
- Text only, by design: fanfare art and sound stay with WL-5.5, which now swaps
      presentation into a working event pipeline instead of building both

### UI Design Concept (prompt library for image/animation generation)

Art direction: warm, storybook flat-vector; earthy browns with gold accents
(matches the `bark-*` / `ink-*` / gold tokens); designed for dark backgrounds
— the chamber scene is pinned dark in both themes (WL-3.3); simple shapes
that export cleanly to SVG; transparent backgrounds for sprites; no text in
images. Feed these as prompts to an image/Lottie generator, then tokenize
colors to the theme.

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

## Milestone 6 — Robustness & Trust 🚧

Goal: the add-ons that make the core dependable on a Pi.

- [ ] **WL-6.1: Data Export / Backup** ⬜

dev S · user med · 🟡

- [ ] Export inventory + transactions + categories to CSV/JSON; import to restore
- [ ] Guards against SD-card loss (SQLite on a Pi has no backup today)

- [ ] **WL-6.2: PWA Install + Offline Scan Queue** ⬜

dev M · user med · 🟢

- [ ] Make the existing manifest installable; service worker for offline shell
- [ ] Queue scans/movements while offline, sync when back online (scan in the garage on bad wifi)

- [ ] **WL-6.3: Performance Pass** 🚧

dev S · user med · 🟡

- Already capped: WL-5.2 shipped `DOT_CAP = 8` (`frontend/src/lib/utils/chamber.ts`), so no single product renders more than 8 dots. What's left is the total across a large pantry — a much smaller concern than per-product growth
- [ ] Drop the list-and-find pattern for products: `products.list()` runs twice in the scan flow just to find one product by EAN. Wants a by-EAN lookup
- [x] Same for profiles: `GET /profiles/{id}` (archived ones resolve; unknown id → 404) replaced the three `profiles.list(true)` + find sites — `refreshProfile()` and the `/profile/[id]` load and post-redeem refetch
- [ ] Page loads refetch whole lists on every `$effect` run (chamber, inventory, activity). Harmless at household scale; revisit only if it becomes visible

- [ ] **WL-6.4: Accessibility & Legibility** ⬜

dev S · user med · 🟡

- [ ] Contrast audit of both themes (the WL-3.3 light values are a first pass — e.g. `danger-500` text on a light card is ~3.8:1; the gold Pantry-dex card border is faint on light); larger tap targets for small hands; screen-reader labels (chamber decorative emojis, stat tables)
- [ ] Destructive confirms (activity delete, inventory delete/merge, category delete — today a plain `Modal`) → Bits UI `AlertDialog`: announced as `alertdialog`, initial focus on Cancel so a stray Enter can't delete. Shares `Dialog`'s core, so near-zero bundle cost

- [ ] **WL-6.5: Interactive Test Coverage** ⬜

dev S · user — · ⚪

- [ ] Component/integration tests for the scan flow and `Select`/`Modal` (the most-used, most-regressed paths) — completes the WL-3.2 leftover (needs a DOM testing library)

- [ ] **WL-6.6: Onboarding / First-Run** ⬜

dev S · user med · 🟡

- [ ] Guided "scan your first item" beat from the empty chamber (doubles as the first achievement)

- [ ] **WL-6.7: Ambidextrous / One-Handed Layout** ⬜

dev S · user med · 🟡

- [ ] Left/right-handed mode: mirror the reach-critical controls (chamber
      consume stepper, primary action buttons, nav/switcher placement) so the
      thumb of the chosen hand covers them one-handed on a phone
- [ ] Handedness toggle in settings, persisted in `localStorage` (default:
      right); a CSS-var/`dir`-style flip, not duplicated markup

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
- [ ] **"Cleared the List"** badge (deferred from WL-5.4) — every item on a trip checked off

- [ ] **WL-7.2: Expiry Date Tracking** ⬜

dev M · user high · 🟢

- [ ] Optional expiry date field on stock-in transactions — per *transaction*, not per product: one product holds several batches with different dates
- [ ] "Expiring soon" badge on inventory items
- [ ] Sort/filter inventory by expiry
- [ ] Push notification (PWA) for items expiring within N days
- [ ] FIFO batch matching on `out` — which batch was just consumed. Prerequisite for both gamification hooks below
- [ ] Consuming-**before-expiry** XP bonus (deferred from WL-5.3) — a branch in `award_transaction`, the single award point
- [ ] **Zero-Waste Week** badge (deferred from WL-5.4) — nothing expired in 7 days

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

- [ ] Match recipe ingredients against current inventory (fuzzy name matching + unit normalization)
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
