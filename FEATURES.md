# Chamber of Secrets — Features

## 1. Vision

A household grocery companion — scan barcodes, know what's in stock,
and let the app figure out what to cook and what to buy. Tracking is
only the beginning: once the pantry is known, the app auto-generates
shopping lists, suggests recipes from a personal database, and can get
creative with on-device AI.

### 1.1 Core Principles

| Principle | Why | Implication |
|-----------|-----|-------------|
| **Lightweight** | Runs 24/7 on a Raspberry Pi — no cloud, no subscription. | SQLite, static frontend, minimal RAM. No heavyweight runtimes. |
| **Portable** | One `docker compose up` on any machine (ARM64 or x86). | Docker/Podman, no host dependencies beyond a container engine. |
| **Easy to use** | This is an every-day tool. If scanning isn't faster than a mental note, nobody will bother. | Mobile-first, one-tap scan-to-stock, minimal clicks. UX trumps features. |
| **Fun to use** | Kids should *want* to scan groceries after a shopping trip. | Satisfying animations, emoji categories, gamification potential. The scan flow should feel like playing, not bookkeeping. |

Easy and fun are the two highest-priority principles. Every feature
must pass the test: *would a 10-year-old use this without being told to?*

### 1.2 Long-Term Vision

Inventory tracking is the foundation, not the product. The real value
emerges from knowing what's in stock:

- **Auto-generated shopping lists** — items below a configurable
  threshold appear on the list automatically; manual additions for
  one-off needs.
- **"What can I cook tonight?"** — match current stock against a
  personal recipe database. Highlight recipes where all ingredients
  are available; suggest close matches with a short shopping delta.
  Recipe format: [Cooklang](https://cooklang.org/) (plain-text,
  git-friendly, ingredient-aware).
- **Creative AI suggestions** — on-device (or local-network) LLM
  proposes meals from available ingredients, substitutes for missing
  ones, or generates new recipes inspired by the user's cooking
  history. Privacy-first: no data leaves the home network.

---

## 2. Core Features

### 2.1 Barcode Scanning

- Point the phone camera at a product barcode (EAN-13 / UPC-A).
- Product details (name, brand, image, nutrition) are fetched from
  [Open Food Facts](https://world.openfoodfacts.org) automatically.
- Cache-first: if the product was scanned before, the local record is
  used; manual refresh re-fetches from the API and snapshots the
  previous data as an immutable revision.
- Record a stock movement (`in` or `out`) with quantity and optional
  unit price directly from the scan page.
- **Manual entry**: when Open Food Facts has no match — or for products
  without a barcode (bakery, loose produce, store brands) — create the
  product yourself from the scan page (name required; brand, category,
  image URL, and EAN optional). The result is a normal trackable product.
  Product images can also be added later from the inventory view.
- **Contribute back to Open Food Facts**: when a real barcode misses OFF and
  you create the product manually, an opt-in checkbox (barcode-only, off by
  default) shares name/brand/category back to OFF as open data (ODbL). The
  submission is proxied through the backend with a server-side OFF account;
  dev/tests target the OFF staging server. Currently text fields only; the
  front-image upload path is wired but dormant behind a config flag
  (`off_contribute_images`).

### 2.2 Inventory

- View current stock levels derived from all recorded transactions
  (`sum(in) - sum(out)`).
- Each product shows name, image, brand, current quantity, and category.
- **Quick stock adjust**: `+`/`−` steppers on each row record an `in`/`out`
  movement (quantity 1) without re-scanning — the one-tap "I ate an apple"
  path. `−` is disabled at zero stock.
- Tap the product image (or placeholder) to open the standard file
  picker. On mobile (touch devices), a small 📷 button opens the rear
  camera directly via `capture="environment"`. Replaces any previous
  image.
- Fuzzy search across all products.
- **Filters**: narrow the list by category and/or a low-stock toggle (items
  needing restock). Filters apply to the fuzzy search too, so search and
  filters combine.

### 2.3 Categories

- Hierarchical categories (parent / child).
- Each category has a name and an optional icon. Children without an icon
  inherit their parent's icon automatically.
- Restock thresholds per category (`restock_target`, `restock_min`) with
  inheritance from parent — children inherit thresholds unless overridden.
- Assign a product to a category on scan or from the inventory view.
- Category management page with folder-style drill-down navigation: tap a
  category with children to slide into its subcategories (iOS-style back
  button, slide animation matching analytics drill-down). One level visible
  at a time, full-width cards, supports arbitrary nesting depth.
- Create, edit, and delete categories at any level. Deletion shows a styled
  confirmation modal (no browser `confirm()`). Deletion is blocked if
  products are still assigned to the category.

### 2.4 Analytics

- Spending breakdown by category over a configurable date range.
- Interactive drill-down donut charts: tap a parent category to slide
  into its children (iOS-style navigation with back button). Categories
  with only one source row are not drillable.
- Line charts for items and spending over time (child and parent views).
- Date-range picker (`since` / `until`).
- Restock overview: per-category view of products needing restocking,
  sorted by urgency.

### 2.5 Audit Trail

- Every product refresh from the EAN API creates a `ProductRevision` —
  an immutable snapshot of the previous product data.
- Full transaction history with timestamps, quantities, and prices.

### 2.6 Mistake Recovery

- **Undo** the last recorded movement with one tap from the scan success
  toast (5-second window).
- **Activity view**: reverse-chronological list of stock movements, globally
  or filtered to a single product. Each movement can be edited (type,
  quantity, unit price) or deleted; stock is derived from transactions at
  query time, so it always reflects the current set.
- **Delete a product** from the inventory view — cascades its transactions,
  revisions, and uploaded image. This frees a category that was previously
  undeletable because a product still referenced it.
- **Merge duplicates**: pick a survivor for a duplicate product; its
  movements are repointed onto the survivor and the duplicate is removed.

### 2.7 Internationalization

- UI available in English (EN) and German (DE).
- Language switcher in the navigation bar.
- All user-facing strings are in locale JSON files (`en.json`, `de.json`).

### 2.8 Visual Style

- Dark color scheme throughout (driven by imagery and backgrounds).
- Proper theming (light/dark toggle, CSS variables) is a future feature
  (see `ROADMAP.md` WL-3.3).

### 2.9 Profiles & Attribution

- Lightweight, login-less profiles — a Netflix/Switch-style picker in the
  nav, next to the language switcher. The app stays fully usable with none
  selected.
- The active profile is persisted in `localStorage` and sent with every stock
  movement (`InventoryTransaction.profile_id`); there is no server session.
  `NULL` attribution means no profile was selected (or a legacy movement).
- Preset avatars: pick a character + color. `avatar_config` is a layered-SVG
  config stored as JSON — `base` is a **stable part id** (`"fox"`), never a
  glyph or SVG markup. Art lives in the frontend bundle and is referenced by id,
  so parts can be redrawn (or swapped from today's emoji stand-in to real SVG)
  without touching stored profiles. WL-5.4 adds a `layers: [{slot, part}]` key
  for unlockable equipment — additive on a JSON column, so no migration.
- Each profile carries `xp` as the source of truth; **level is derived**
  (`level_for_xp`), never stored. Achievements and unlocks land in WL-5.4 —
  this is their foundation.

### 2.9a Progression — XP, Levels & Streaks

- Every stock movement attributed to a profile awards XP server-side
  (`services/progression.py`): stocking something is worth more than using it
  up. This is the *only* place XP is granted — levels, and later achievements
  and rewards, all derive from `Profile.xp`.
- A daily streak rolls along with it: acting on a consecutive day extends
  `current_streak`, a gap restarts it, and `longest_streak` keeps the record.
- XP is not clawed back when a movement is undone — a few XP for a mis-tap is
  cheaper than an award ledger.
- The frontend mirrors the active profile in one store (`$lib/progression.ts`)
  that every gamification feature reads from. It also derives the chamber's
  visual state — a **stage** (1–5, grows with level) and a **guardian mood**
  (`thriving` / `content` / `sparse` / `forlorn`, from how much of the pantry
  needs restocking). Both are plain data rendered as `data-stage` / `data-mood`
  on the scene; the art that reacts to them is WL-5.5.

### 2.9b Achievements

- Badges are earned automatically and never lost. Only the fact that one was
  earned is stored (`profile_achievements`, one row per profile + badge key) —
  every condition is re-derived from data that already exists, so re-checking is
  idempotent and a new rule retro-awards itself on the next movement.
- Shipped badges: **First Scan** (stock anything), **Well Stocked** (50 items
  stocked), **Week Streak** (7 consecutive days), **Chamber Keeper** (level 5)
  and **Explorer** (contribute a product to Open Food Facts, see 2.7).
- Stocking milestones count `in` movements only — using things up doesn't
  advance them.
- The backend stores keys; names, descriptions and art are resolved
  client-side, so a badge can be renamed or redrawn without a migration. The
  glyphs shown in the chamber ledger are placeholders until WL-5.5.
- Newly earned badges are detected by diffing the active profile on refresh, so
  every award path announces itself the same way — a toast in the chamber.
- Each profile has a dedicated progress page (`/profile/[id]`) reached from the
  profile picker (the `›` on a profile row): avatar, level with an XP bar toward
  the next level, day streak, and the full badge grid showing earned badges
  alongside still-locked ones. A standalone route so a later navigation redesign
  can place it freely.

### 2.10 Deployment

- Docker / Podman Compose stack (backend + nginx frontend).
- TLS via mkcert for local HTTPS (trusted on mobile after CA install).
- Optional Cloudflare Tunnel for remote access without port-forwarding.
- Designed for Raspberry Pi (ARM64) but runs on any Docker host.

### 2.11 The Chamber

- The playful home view: current stock rendered as emoji piles on a
  storybook background, one emoji per unit (capped per product), grouped
  into per-category Gaussian blobs on the chamber floor. Emoji are guessed
  from the product/category name, or the category's custom icon/image.
- **Tap-to-consume**: tap an item to use some up. Because emoji are lossy
  (the same 🥛 can stand for several products), the tap opens a sheet that
  names the item(s) under it — a confirmation for one, a chooser for
  several — with a quantity stepper so you can consume more than one at
  once. Confirming records an `out` and the emoji poofs away (scale + fade
  + spin; respects `prefers-reduced-motion`). The *tapped* emoji is the one
  that vanishes, and a big pile refills from its reserve rather than gapping.
  This doubles as the quick-consume path alongside the inventory `+`/`−`
  steppers.
- **Undo**: a 5-second toast (with an explicit ✕ dismiss) reverses an
  accidental consume by deleting the transaction — stock is derived, so the
  emoji simply returns. A new consume replaces the toast; undo targets the
  latest action.
- A floating 📜 ledger shows in-stock / needs-restocking / total counts, plus
  the active profile's XP, level, and current streak.
- The chamber lights up as the profile levels (stage) and its guardian reacts
  to how well stocked the pantry is (mood) — see 2.9a.
- Placement is deterministic and stable: each emoji keeps its spot across
  reloads and as stock changes, so consuming one never reshuffles the rest.

---

## 3. Data Model

**Categories** — hierarchical (self-referencing `parent_id`), icon,
restock thresholds (`restock_target`, `restock_min`, `restock_inherit`).

**Products** — identified by EAN barcode; linked to a category.

**ProductRevisions** — immutable snapshot created on each product refresh.

**InventoryTransactions** — `type: in | out` with quantity and unit price;
current stock is computed at query time. Optional `profile_id` attributes the
movement to a profile (nullable).

**Profiles** — login-less identity: `name`, `avatar_config` (JSON: layered-SVG
part ids), `xp` (source of truth; level derived), streak fields, `locale`,
`is_archived`.

**Profile achievements** — append-only `profile_id` + `achievement_key` rows,
unique per pair. The unlock table (owned cosmetics) arrives with the avatar
compositor.

---

## 4. API Surface

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/products/` | List products with computed stock |
| GET | `/api/products/{id}` | Get one product with computed stock |
| GET | `/api/products/{id}/revisions` | List a product's revision history |
| GET | `/api/products/lookup/{ean}` | EAN lookup (cache → Open Food Facts) |
| POST | `/api/products/` | Create a product (manual entry) |
| PATCH | `/api/products/{id}` | Update product (category, image URL) |
| POST | `/api/products/{id}/refresh` | Re-fetch from API, snapshot old data |
| POST | `/api/products/{id}/image` | Upload product image (multipart) |
| DELETE | `/api/products/{id}/image` | Remove product image |
| DELETE | `/api/products/{id}` | Delete product (cascades movements/revisions/image) |
| POST | `/api/products/merge` | Merge a duplicate into another product |
| POST | `/api/products/{id}/contribute` | Submit a barcode product back to Open Food Facts (WL-4.6); `?profile_id=` earns "Explorer" |
| GET | `/api/transactions/` | List transactions (optional `product_id`) |
| POST | `/api/transactions/` | Record a stock movement |
| PATCH | `/api/transactions/{id}` | Edit a movement |
| DELETE | `/api/transactions/{id}` | Delete a movement (powers undo) |
| GET | `/api/categories/` | List categories |
| POST | `/api/categories/` | Create category |
| PATCH | `/api/categories/{id}` | Update category |
| DELETE | `/api/categories/{id}` | Delete category (409 if products assigned) |
| GET | `/api/analytics/spending` | Spending by category (date range) |
| GET | `/api/analytics/timeseries` | Spending over time |
| GET | `/api/analytics/restock-overview` | Products needing restock by category |
| GET | `/api/profiles/` | List profiles (optional `include_archived`) |
| POST | `/api/profiles/` | Create a profile |
| PATCH | `/api/profiles/{id}` | Update a profile (rename, avatar, archive) |
| GET | `/api/health` | Health check |
