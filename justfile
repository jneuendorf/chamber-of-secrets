set dotenv-load

host := "0.0.0.0"

# list available recipes
default:
    @just --list

# start the FastAPI backend with auto-reload
backend:
    cd backend && uv run uvicorn app.main:app --reload --host {{ host }}

# start the SvelteKit dev server
frontend:
    cd frontend && bun run dev --host {{ host }}

# start both backend and frontend
dev:
    just backend & just frontend & wait

# generate TLS certs with mkcert if they don't already exist
certs:
    if [ ! -f certs/cert.pem ] || [ ! -f certs/key.pem ]; then \
        ./scripts/setup-certs.sh; \
    fi

# build images and start the full stack in Docker (production mode)
up: certs
    docker compose up --build -d

# stop and remove Docker containers
down:
    docker compose down

# tail logs from all Docker services
logs:
    docker compose logs -f

# build the frontend for production
build-frontend:
    cd frontend && bun run build

# type-check the frontend
check-frontend:
    cd frontend && bun run check

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

# lint the backend with ruff
lint:
    cd backend && uv run ruff check app/

# format backend (ruff) and frontend (prettier)
format:
    cd backend && uv run ruff format app/
    cd frontend && bun run format

# check formatting without writing changes
format-check:
    cd backend && uv run ruff format --check app/
    cd frontend && bun run format:check
