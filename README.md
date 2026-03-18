# Chamber of Secrets

A personal grocery inventory tracker. Scan product barcodes, record stock movements, and analyse spending by category. Designed to run on a Raspberry Pi and be accessible from mobile devices over HTTPS.

---

## What it does

- **Scan** — point a phone camera at a barcode; product details are fetched automatically from [Open Food Facts](https://world.openfoodfacts.org)
- **Inventory** — view current stock levels derived from all recorded transactions
- **Analytics** — spending breakdown by category over a configurable date range
- **Audit trail** — every product refresh snapshots the previous data as an immutable revision

---

## Tech stack

| Layer | Technology |
|---|---|
| Backend | FastAPI · SQLAlchemy 2 · Alembic · SQLite |
| Frontend | SvelteKit 2 · Svelte 5 · TypeScript · Tailwind CSS 4 |
| i18n | svelte-i18n (EN / DE) |
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
│   │   ├── main.py           # FastAPI app, startup migrations, CORS
│   │   ├── models.py         # SQLAlchemy models
│   │   ├── schemas.py        # Pydantic I/O schemas
│   │   ├── config.py         # Settings (APP_* env vars)
│   │   ├── database.py       # Engine and session factory
│   │   ├── routers/          # products, transactions, categories, analytics
│   │   └── services/
│   │       └── ean_lookup.py # Open Food Facts integration (cache-first)
│   └── alembic/              # Database migrations
├── frontend/
│   └── src/
│       ├── routes/           # +page.svelte per route (/, /scan, /inventory, /analytics, /docs)
│       ├── lib/
│       │   ├── api/client.ts # Typed API client
│       │   ├── components/   # BarcodeScanner, LocaleSwitcher
│       │   └── i18n/         # en.json, de.json, init
│       └── app.css           # Tailwind entry point + global base styles
├── scripts/
│   └── setup-certs.sh        # mkcert wrapper (auto-detects local IP)
├── frontend/nginx.conf       # HTTPS on 443, /api/ proxy to backend, SPA fallback
├── frontend/40-setup-certs.sh# Container entrypoint: copies real certs or generates self-signed
├── compose.yaml              # backend + frontend services, optional cloudflared
├── justfile                  # Task runner (see below)
└── .env.example              # Environment variable reference
```

---

## Data model

**Categories** — hierarchical (self-referencing `parent_id`)

**Products** — identified by EAN barcode; linked to a category

**ProductRevisions** — immutable snapshot created each time a product is refreshed from the EAN API

**InventoryTransactions** — each stock movement is recorded as `type: in | out` with quantity and unit price; current stock is computed as `Σin − Σout`

---

## API

| Method | Path | Description |
|---|---|---|
| GET | `/api/products/` | List products with computed stock |
| GET | `/api/products/lookup/{ean}` | EAN lookup (DB cache → Open Food Facts) |
| POST | `/api/products/{id}/refresh` | Re-fetch from EAN API, snapshot old data |
| GET | `/api/transactions/` | List transactions |
| POST | `/api/transactions/` | Record a stock movement |
| GET | `/api/categories/` | List categories |
| GET | `/api/analytics/spending` | Spending by category (optional `since`/`until`) |
| GET | `/api/health` | Health check |

Interactive docs are available at `/api/docs` (Swagger UI).

---

## Running locally (dev)

```sh
just dev          # backend (uvicorn --reload) + frontend (vite) in parallel
just backend      # backend only
just frontend     # frontend only
```

Backend: `http://localhost:8000` · Frontend: `http://localhost:5173`

---

## Running with Docker or Podman (production)

```sh
just up           # generate TLS certs if missing, build images, start stack
just down         # stop and remove containers
just logs         # tail logs from all services
```

To use Podman with the same `just` commands, set `CONTAINER_ENGINE=podman`:

```sh
CONTAINER_ENGINE=podman just up
CONTAINER_ENGINE=podman just down
CONTAINER_ENGINE=podman just logs
```

You can also export it once per shell session:

```sh
export CONTAINER_ENGINE=podman
just up
just down
just logs
```

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

---

## Configuration

Backend is configured via environment variables prefixed with `APP_`:

| Variable | Default | Description |
|---|---|---|
| `APP_DATABASE_URL` | `sqlite:///./data/inventory.db` | SQLAlchemy database URL |
| `APP_CORS_ORIGINS` | `["http://localhost:5173"]` | Allowed CORS origins (JSON array) |
| `APP_EAN_API_BASE_URL` | `https://world.openfoodfacts.org/api/v2` | Open Food Facts base URL |

Copy `.env.example` to `.env` and fill in values as needed.

### Optional: Cloudflare Tunnel

Expose the app over HTTPS from anywhere without port-forwarding. See the commented-out `cloudflared` service in `compose.yaml` for setup instructions.

---

## Code quality

```sh
just lint           # ruff lint (backend)
just format         # ruff format (backend) + prettier (frontend)
just format-check   # check formatting without writing
just check-frontend # svelte-check + TypeScript
```
