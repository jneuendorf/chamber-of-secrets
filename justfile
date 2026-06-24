set dotenv-load

host := "0.0.0.0"
container_engine := env('CONTAINER_ENGINE', 'podman')

# list available recipes
default:
    @just --list

# --- Dev & Build ---

# start the FastAPI backend with auto-reload
backend:
    cd backend && uv run uvicorn app.main:app --reload --host {{ host }}

# start the SvelteKit dev server
frontend:
    cd frontend && bun run dev --host {{ host }}

# start both backend and frontend
dev:
    just backend & just frontend & wait

# build the frontend for production
build-frontend:
    cd frontend && bun run build

# --- Quality: lint ---

# lint all. Biome defaults to --staged; pass "" for all files
lint *SCOPE="--staged": (lint-frontend SCOPE) lint-backend

# lint frontend with biome (--staged by default; pass "" for all files)
lint-frontend *SCOPE="--staged":
    cd frontend && bun run lint -- {{ SCOPE }}

# lint backend with ruff
lint-backend:
    cd backend && uv run ruff check app/

# --- Quality: format ---

# format all. Biome defaults to --staged; pass "" for all files
format *SCOPE="--staged": (format-frontend SCOPE) format-backend

# format frontend: Biome (non-Svelte) + Prettier (Svelte). --staged by default; pass "" for all files
format-frontend *SCOPE="--staged": (format-frontend-biome SCOPE) (prettier-svelte "--write" SCOPE)

# format non-Svelte frontend files with Biome
format-frontend-biome *SCOPE="--staged":
    cd frontend && bun run format -- {{ SCOPE }}

# format backend with ruff
format-backend:
    cd backend && uv run ruff format app/

# check formatting without writing. Biome defaults to --staged; pass "" for all files
format-check *SCOPE="--staged": (format-check-frontend SCOPE) format-check-backend

# check frontend formatting: Biome (non-Svelte) + Prettier (Svelte). --staged by default; pass "" for all files
format-check-frontend *SCOPE="--staged": (format-check-frontend-biome SCOPE) (prettier-svelte "--check" SCOPE)

# check non-Svelte frontend formatting with Biome
format-check-frontend-biome *SCOPE="--staged":
    cd frontend && bun run format:check -- {{ SCOPE }}

# run Prettier on Svelte files (Biome can't format .svelte yet). MODE = --write | --check
[private]
prettier-svelte MODE *SCOPE="--staged":
    #!/usr/bin/env sh
    set -eu
    cd frontend
    if [ "{{ SCOPE }}" = "--staged" ]; then
        files=$(git diff --cached --name-only --relative --diff-filter=ACMR -- '*.svelte')
        if [ -n "$files" ]; then
            printf '%s\n' "$files" | xargs bunx prettier {{ MODE }}
        else
            echo "prettier: no staged .svelte files"
        fi
    else
        bunx prettier {{ MODE }} "**/*.svelte"
    fi

# check backend formatting
format-check-backend:
    cd backend && uv run ruff format --check app/

# --- Quality: typecheck ---

# typecheck frontend (svelte-check)
typecheck-frontend:
    cd frontend && bun run check

# --- Quality: test ---

# run all tests
test: test-frontend test-backend

# run frontend tests
test-frontend:
    cd frontend && bun test

# run backend tests
test-backend:
    cd backend && uv run python -m unittest discover -s tests -v

# --- Quality: check (lint + typecheck + test) ---

# check all. Biome defaults to --staged; pass "" for all files
check *SCOPE="--staged": (check-frontend SCOPE) check-backend

check-all: (check "")

# full biome check: lint + format + assist (--staged by default; pass "" for all files)
biome-check-frontend *SCOPE="--staged":
    cd frontend && bun run biome:check -- {{ SCOPE }}

# check frontend: biome check + prettier (svelte) + typecheck + test (--staged applies to biome/prettier)
check-frontend *SCOPE="--staged": (biome-check-frontend SCOPE) (prettier-svelte "--check" SCOPE) typecheck-frontend test-frontend

# check backend: lint + test
check-backend: lint-backend test-backend

# --- Database ---

# generate a new migration: just db-make-migrations "add expiry date"
db-make-migrations msg:
    cd backend && uv run alembic revision --autogenerate -m "{{ msg }}"

# apply all pending migrations
db-migrate:
    cd backend && uv run alembic upgrade head

# roll back migrations: just db-rollback (1 step) or just db-rollback 3
db-rollback steps="1":
    cd backend && uv run alembic downgrade -{{ steps }}

# show current migration and history
db-status:
    cd backend && uv run alembic current && uv run alembic history --indicate-current

# seed the database with the sample food catalog (asks for confirmation if data exists)
seed:
    just db-migrate
    cd backend && uv run python scripts/seed.py

# --- Deployment ---

# generate TLS certs with mkcert if they don't already exist
certs:
    if [ ! -f certs/cert.pem ] || [ ! -f certs/key.pem ]; then \
        ./scripts/setup-certs.sh; \
    fi

# build images and start the full stack in containers (production mode)
# set CONTAINER_ENGINE=docker to use Docker instead of Podman
up: certs
    {{ container_engine }} compose up --build -d

# stop and remove containers
down:
    {{ container_engine }} compose down

# tail logs from all container services
logs:
    {{ container_engine }} compose logs -f
