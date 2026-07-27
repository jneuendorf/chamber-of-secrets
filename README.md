# Chamber of Secrets

A household grocery companion. Scan product barcodes, track what's in stock, analyze spending — and make the whole thing fun enough that kids want to do the scanning. Designed to run on a Raspberry Pi and be accessible from mobile devices over HTTPS.

---

## What it does

- **Scan** — point a phone camera at a barcode; product details are fetched automatically from [Open Food Facts](https://world.openfoodfacts.org). No match? Create the product manually, and optionally contribute it back to OFF as open data
- **Inventory** — current stock levels derived from all recorded transactions, with fuzzy search, category/low-stock filters, and `+`/`−` quick adjust
- **Chamber** — the playful home view: stock rendered as emoji piles you can tap to consume, with a 5-second undo
- **Analytics** — spending breakdown by category over a configurable date range, plus a restock overview
- **Profiles & progression** — login-less profiles earn XP, levels, streaks and badges for stocking and consuming; a household can tie real-life rewards to a level and mark them redeemed
- **Audit trail** — every product refresh snapshots the previous data as an immutable revision; every movement is editable and reversible

See [`FEATURES.md`](FEATURES.md) for the full feature spec and [`ROADMAP.md`](ROADMAP.md) for delivery status.

---

## Tech stack

| Layer | Technology |
|---|---|
| Backend | FastAPI · SQLAlchemy 2 · Alembic · SQLite |
| Frontend | SvelteKit 2 · Svelte 5 · TypeScript · Tailwind CSS 4 |
| UI primitives | Bits UI (headless, accessible) |
| i18n | svelte-i18n (EN / DE) |
| Lint & format | Biome 2 (frontend) · Prettier (`.svelte` only) · Ruff (backend) |
| Type check | svelte-check (frontend) · ty (backend) |
| Build & package | Bun · uv |
| Containers | Docker Compose / Podman Compose · nginx (TLS) |
| TLS (local) | mkcert |
| Optional tunnel | Cloudflare Tunnel |

---

## Project structure

```
chamber-of-secrets/
├── backend/
│   ├── app/
│   │   ├── main.py               # FastAPI app, startup migrations, CORS
│   │   ├── models.py             # SQLAlchemy models
│   │   ├── schemas.py            # Pydantic I/O schemas — the wire contract's source of truth
│   │   ├── config.py             # Settings (APP_* env vars)
│   │   ├── database.py           # Engine + session factory (SQLite FKs enabled on connect)
│   │   ├── routers/              # products, transactions, categories, analytics, profiles, rewards
│   │   └── services/
│   │       ├── ean_lookup.py     # Open Food Facts lookup (cache-first)
│   │       ├── off_contribute.py # Open Food Facts write-back
│   │       ├── progression.py    # the single XP / streak award point
│   │       ├── achievements.py   # badge rules, all derived from existing data
│   │       └── restock.py        # category restock thresholds (with inheritance)
│   ├── scripts/
│   │   ├── seed.py               # sample catalog, profiles and reward tiers
│   │   └── dump_openapi.py       # feeds `just types`
│   └── alembic/                  # Database migrations
├── frontend/
│   └── src/
│       ├── routes/               # / (→ /chamber), /scan, /inventory, /activity,
│       │                         #   /categories, /analytics, /chamber, /profile/[id], /docs
│       ├── lib/
│       │   ├── api/client.ts     # Typed API client (aliases the generated schema.d.ts)
│       │   ├── components/       # Avatar, BarcodeScanner, CategoryPicker, ConsumeSheet,
│       │   │                     #   DrillDownDonut, FuzzySearchOverlay, LocaleSwitcher,
│       │   │                     #   Modal, ProfileSwitcher, Select
│       │   ├── utils/            # pure, unit-tested: analytics, category, chamber, scan
│       │   ├── profiles.ts       # active-profile store (localStorage) + avatar presets
│       │   ├── progression.ts    # XP / level / streak store, chamber stage + guardian mood
│       │   ├── theme.ts          # chart palette + theme tokens for canvas
│       │   └── i18n/             # en.json, de.json, init
│       └── app.css               # Tailwind entry point, @theme tokens, global base styles
├── scripts/
│   └── setup-certs.sh            # mkcert wrapper (auto-detects local IP)
├── frontend/nginx.conf           # HTTPS on 443, /api/ proxy to backend, SPA fallback
├── frontend/40-setup-certs.sh    # Container entrypoint: real certs or self-signed fallback
├── compose.yaml                  # backend + frontend services, optional cloudflared
├── justfile                      # Task runner (see below)
└── .env.example                  # Environment variable reference
```

---

## Data model

**Categories** — hierarchical (self-referencing `parent_id`); restock thresholds inherit from the parent

**Products** — identified by EAN barcode; linked to a category

**ProductRevisions** — immutable snapshot created each time a product is refreshed from the EAN API

**InventoryTransactions** — each stock movement is recorded as `type: in | out` with quantity and unit price; current stock is computed as `Σin − Σout`. An optional `profile_id` attributes the movement (nullable = no profile selected)

**Profiles** — login-less identity: name, `avatar_config` (JSON), `xp` (source of truth — level is *derived*, never stored), streak fields

**ProfileAchievements** — append-only `profile_id` + `achievement_key`, unique per pair. Only the fact that a badge was earned is stored; every condition is re-derived, so re-checking is idempotent

**RewardTiers** — household-wide real-life rewards: a level (≥ 2) plus free text. Unlocking is derived (`level >= tier.level`), never stored

**ProfileRewards** — the one per-profile bit that *is* stored: which rewards a profile marked redeemed. Unique per `(profile, tier)`; cascades when a tier is deleted

---

## API

| Method | Path | Description |
|---|---|---|
| GET | `/api/products/` | List products with computed stock |
| GET | `/api/products/{id}` | Get one product with computed stock |
| GET | `/api/products/{id}/revisions` | List a product's revision history |
| GET | `/api/products/lookup/{ean}` | EAN lookup (DB cache → Open Food Facts) |
| POST | `/api/products/` | Create a product (manual entry) |
| PATCH | `/api/products/{id}` | Update product (category, image URL) |
| POST | `/api/products/{id}/refresh` | Re-fetch from EAN API, snapshot old data |
| POST | `/api/products/{id}/image` | Upload product image (multipart) |
| DELETE | `/api/products/{id}/image` | Remove product image |
| DELETE | `/api/products/{id}` | Delete product (cascades movements/revisions/image) |
| POST | `/api/products/merge` | Merge a duplicate into another product |
| POST | `/api/products/{id}/contribute` | Submit a barcode product back to Open Food Facts; `?profile_id=` earns "Explorer" |
| GET | `/api/transactions/` | List transactions (optional `product_id`) |
| POST | `/api/transactions/` | Record a stock movement |
| PATCH | `/api/transactions/{id}` | Edit a movement |
| DELETE | `/api/transactions/{id}` | Delete a movement (powers undo) |
| GET | `/api/categories/` | List categories |
| POST | `/api/categories/` | Create category |
| PATCH | `/api/categories/{id}` | Update category |
| DELETE | `/api/categories/{id}` | Delete category (409 if products assigned) |
| GET | `/api/analytics/spending` | Spending by category (optional `since`/`until`) |
| GET | `/api/analytics/timeseries` | Spending over time |
| GET | `/api/analytics/restock-overview` | Products needing restock by category |
| GET | `/api/profiles/` | List profiles (optional `include_archived`) |
| POST | `/api/profiles/` | Create a profile |
| PATCH | `/api/profiles/{id}` | Update a profile (rename, avatar, archive) |
| GET | `/api/rewards/` | List household reward tiers (sorted by level) |
| POST | `/api/rewards/` | Create a reward tier (level ≥ 2 + description) |
| DELETE | `/api/rewards/{id}` | Delete a reward tier (cascades redemptions) |
| POST | `/api/rewards/{id}/redemption?profile_id=` | Mark a reward redeemed for a profile (idempotent; 409 if not unlocked) |
| DELETE | `/api/rewards/{id}/redemption?profile_id=` | Un-redeem for a profile (idempotent) |
| GET | `/api/health` | Health check |

Interactive docs are available at `/api/docs` (Swagger UI).

---

## Running locally (dev)

```sh
just dev          # backend (uvicorn --reload) + frontend (vite) in parallel
just backend      # backend only
just frontend     # frontend only
just seed         # load the sample catalog, profiles and reward tiers
```

Backend: `http://localhost:8000` · Frontend: `http://localhost:5173`

### Scanning on a phone

Camera access needs a secure context, which the plain-HTTP dev server on your LAN
IP is not. Serve the dev frontend over TLS with the mkcert certs instead:

```sh
just certs        # once — generates certs/ covering localhost + your LAN IP
just dev https    # or: just frontend https
```

Then open `https://<your-lan-ip>:5173` on the phone (install the mkcert root CA
first — see below). Without this, the scanner shows an "open over HTTPS" message
rather than a camera.

---

## Running with Docker or Podman (production)

```sh
just up           # generate TLS certs if missing, build images, start stack
just down         # stop and remove containers
just logs         # tail logs from all services
```

These use **Docker** by default. To use Podman with the same `just` commands, set
`CONTAINER_ENGINE=podman`:

```sh
CONTAINER_ENGINE=podman just up
```

Or export it once per shell session:

```sh
export CONTAINER_ENGINE=podman
just up
```

Or make it permanent for this checkout by uncommenting `CONTAINER_ENGINE` in your
`.env` — the justfile loads it (`set dotenv-load`), so a value there wins over the
built-in default.

On first run, `just up` calls `scripts/setup-certs.sh` which uses **mkcert** to generate a locally-trusted certificate covering `localhost` and your machine's LAN IP. Install mkcert first:

```sh
brew install mkcert   # macOS
```

To trust the certificate on a mobile device, install the mkcert root CA:

- **iOS**: copy `$(mkcert -CAROOT)/rootCA.pem` to the device → Settings → General → VPN & Device Management → install, then enable in Certificate Trust Settings
- **Android**: Settings → Security → Install from storage → pick `rootCA.pem`

The frontend container generates a self-signed fallback certificate at startup if no certs are mounted, so the stack always starts even before mkcert is set up (browsers will show a warning until real certs are installed).

---

## Database migrations

```sh
just db-make-migrations "add expiry date"   # generate a new migration
just db-migrate                              # apply all pending migrations
just db-rollback                             # roll back one step
just db-rollback 3                           # roll back three steps
just db-status                               # current revision + history
```

> **Pre-alpha:** there is deliberately only one migration. Schema changes are
> folded into `0001_initial_schema.py` instead of adding revision files, so
> `just db-make-migrations` is not the current workflow. See
> [`backend/README.md`](backend/README.md) for the details and the SQLite
> `batch_alter_table` caveat.

---

## Configuration

Backend is configured via environment variables prefixed with `APP_`:

| Variable | Default | Description |
|---|---|---|
| `APP_DATABASE_URL` | `sqlite:///./data/inventory.db` | SQLAlchemy database URL |
| `APP_CORS_ORIGINS` | `["http://localhost:5173"]` | Allowed CORS origins (JSON array) |
| `APP_EAN_API_BASE_URL` | `https://world.openfoodfacts.org/api/v2` | Open Food Facts base URL (reads) |

### Contributing back to Open Food Facts

Write-back defaults target the OFF **staging** server, so dev and tests never
touch production data. A production deploy overrides these and sets
`APP_OFF_SITE_AUTH=` (empty) to drop the staging gate.

| Variable | Default | Description |
|---|---|---|
| `APP_OFF_WRITE_BASE_URL` | `https://world.openfoodfacts.net` | OFF base URL for writes (staging by default) |
| `APP_OFF_SITE_AUTH` | `off:off` | HTTP basic auth gating the staging site; empty in production |
| `APP_OFF_USER_ID` | `off` | OFF account used for submissions |
| `APP_OFF_PASSWORD` | `off` | Password for that account |
| `APP_OFF_USER_AGENT` | `ChamberOfSecrets/1.0 (…)` | Descriptive User-Agent, required by OFF |
| `APP_OFF_CONTRIBUTE_IMAGES` | `false` | Front-image upload — fully wired but dormant until the scan flow captures a photo |

Copy `.env.example` to `.env` and fill in values as needed.

### Optional: Cloudflare Tunnel

Expose the app over HTTPS from anywhere without port-forwarding. See the commented-out `cloudflared` service in `compose.yaml` for setup instructions.

---

## Code quality

```sh
just check          # lint + format + typecheck + test, both layers
just check-all      # same, but over all files instead of just staged ones
just check-frontend # biome check + prettier (svelte) + svelte-check + bun test
just check-backend  # ruff + ty type check + tests
just test           # tests only, both layers
just lint           # biome (frontend) + ruff (backend)
just format         # biome + prettier (frontend) + ruff (backend)
just format-check   # check formatting without writing
just types          # regenerate frontend API types from the backend's OpenAPI schema
```

Frontend recipes default to **staged files only**; pass `""` to cover everything
(`just lint-frontend ""`). Biome owns JS/TS/JSON/CSS, Prettier owns `.svelte`
(Biome can't format it yet) — `just format-frontend` routes both, so don't
hand-format Svelte.

`frontend/src/lib/api/schema.d.ts` is **generated** from the backend's OpenAPI
schema and is not committed. `just typecheck-frontend` regenerates it first, so
it can't go stale; never edit it by hand.
