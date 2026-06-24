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

### 2.2 Inventory

- View current stock levels derived from all recorded transactions
  (`sum(in) - sum(out)`).
- Each product shows name, image, brand, current quantity, and category.
- Tap the product image (or placeholder) to open the standard file
  picker. On mobile (touch devices), a small 📷 button opens the rear
  camera directly via `capture="environment"`. Replaces any previous
  image.
- Fuzzy search across all products.

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

### 2.6 Internationalisation

- UI available in English (EN) and German (DE).
- Language switcher in the navigation bar.
- All user-facing strings are in locale JSON files (`en.json`, `de.json`).

### 2.7 Visual Style

- Dark colour scheme throughout (driven by imagery and backgrounds).
- Proper theming (light/dark toggle, CSS variables) is a future feature
  (see `ROADMAP.md` WL-3.3).

### 2.8 Deployment

- Docker / Podman Compose stack (backend + nginx frontend).
- TLS via mkcert for local HTTPS (trusted on mobile after CA install).
- Optional Cloudflare Tunnel for remote access without port-forwarding.
- Designed for Raspberry Pi (ARM64) but runs on any Docker host.

---

## 3. Data Model

**Categories** — hierarchical (self-referencing `parent_id`), icon,
restock thresholds (`restock_target`, `restock_min`, `restock_inherit`).

**Products** — identified by EAN barcode; linked to a category.

**ProductRevisions** — immutable snapshot created on each product refresh.

**InventoryTransactions** — `type: in | out` with quantity and unit price;
current stock is computed at query time.

---

## 4. API Surface

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/products/` | List products with computed stock |
| GET | `/api/products/lookup/{ean}` | EAN lookup (cache → Open Food Facts) |
| POST | `/api/products/{id}/refresh` | Re-fetch from API, snapshot old data |
| POST | `/api/products/{id}/image` | Upload product image (multipart) |
| DELETE | `/api/products/{id}/image` | Remove product image |
| GET | `/api/transactions/` | List transactions |
| POST | `/api/transactions/` | Record a stock movement |
| GET | `/api/categories/` | List categories |
| POST | `/api/categories/` | Create category |
| PATCH | `/api/categories/{id}` | Update category |
| DELETE | `/api/categories/{id}` | Delete category (409 if products assigned) |
| GET | `/api/analytics/spending` | Spending by category (date range) |
| GET | `/api/analytics/timeseries` | Spending over time |
| GET | `/api/analytics/restock-overview` | Products needing restock by category |
| GET | `/api/health` | Health check |
