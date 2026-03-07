

## Database Migrations

`alembic/env.py` — wired to pull `database_url` from `app.config.settings` and `target_metadata` from `Base.metadata`. `render_as_batch=True` is set in both offline and online modes — this is critical for SQLite, which doesn't support `ALTER TABLE` directly (Alembic works around it by recreating tables in a batch).

`alembic.ini` — URL left blank (env.py provides it), ruff post-write hook enabled so generated revision files are auto-formatted.

`app/main.py` — `create_all` replaced with `alembic upgrade head` in the lifespan. The DB schema is now always at the latest migration on every server start, including on deploy.

`alembic/versions/…_initial.py` — the initial migration captures all four current tables.
