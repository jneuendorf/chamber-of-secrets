# Backend notes

## Database Migrations

`alembic/env.py` — wired to pull `database_url` from `app.config.settings` and `target_metadata` from `Base.metadata`. `render_as_batch=True` is set in both offline and online modes — this matters for SQLite, which has no `ALTER COLUMN` and only limited `DROP COLUMN` support (Alembic works around it by recreating the table).

**`render_as_batch` only affects how autogenerate *renders* a migration, not how it runs.** A standalone `op.alter_column(…, server_default=…)` or `op.drop_column(…)` still fails at runtime against SQLite even though the generated file looks correct. Wrap those changes in `with op.batch_alter_table(…) as batch_op:` yourself. `tests/test_migrations.py` runs `upgrade head` (and a full downgrade/re-upgrade) on a fresh database, which is what catches this.

`alembic.ini` — URL left blank (env.py provides it), ruff post-write hook enabled so generated revision files are auto-formatted.

`app/main.py` — the lifespan runs `alembic upgrade head` **and then** `Base.metadata.create_all`. Migrations are the real schema source; `create_all` is a safety net for tables no migration covers yet. That's not redundant: under the single-migration rule below, a dev database already stamped at `0001` won't re-run it, so `create_all` is what materializes a newly added model on the next start.

`alembic/versions/0001_initial_schema.py` — currently the only migration. It creates all eight tables: `categories`, `products`, `product_revisions`, `profiles`, `inventory_transactions`, `profile_achievements`, `reward_tiers`, `profile_rewards`.

### Pre-alpha: one migration, not a history

There are no users and no data worth preserving yet, so schema changes are **folded into `0001_initial_schema.py`** rather than added as new revision files. The migration history stays a single file until the first real deployment.

This is why `just db-make-migrations` — documented in the root README as the general workflow — is *not* the path to take right now: generate the DDL if it helps, then merge it into `0001` (both `upgrade()` and `downgrade()`) and delete the generated file. Each `create_table` in `0001` is guarded by an `if "…" not in existing:` check, so re-running it against an existing database is safe.
