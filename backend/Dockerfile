# Copy uv binary from the official image — avoids installing it via pip
FROM ghcr.io/astral-sh/uv:latest AS uv

FROM python:3.14-slim
COPY --from=uv /uv /bin/uv

WORKDIR /app

# Install dependencies first (separate layer — only re-runs when lockfile changes).
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy source and install the project itself.
COPY . .
RUN uv sync --frozen --no-dev

# Put the venv on PATH so we can call uvicorn directly without `uv run`
# (which would re-sync the environment and pull in dev dependencies).
ENV PATH="/app/.venv/bin:$PATH"

# data/ is mounted as a volume at runtime; create the dir so Alembic is happy
# if the volume isn't mounted (e.g. local dev without compose).
RUN mkdir -p /app/data

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
