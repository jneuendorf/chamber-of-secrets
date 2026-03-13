"""add category restock policy columns

Revision ID: 0002_add_category_restock_policy
Revises: 0001_initial_schema
Create Date: 2026-03-12

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect as sa_inspect

# revision identifiers, used by Alembic.
revision: str = "0002_add_category_restock_policy"
down_revision: str | Sequence[str] | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    existing_tables = inspector.get_table_names()

    if "categories" not in existing_tables:
        return

    existing_columns = {c["name"] for c in inspector.get_columns("categories")}

    if "restock_target" not in existing_columns:
        op.add_column("categories", sa.Column("restock_target", sa.Float(), nullable=True))

    if "restock_min" not in existing_columns:
        op.add_column("categories", sa.Column("restock_min", sa.Float(), nullable=True))

    if "restock_inherit" not in existing_columns:
        op.add_column(
            "categories",
            sa.Column(
                "restock_inherit",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            ),
        )
        op.alter_column("categories", "restock_inherit", server_default=None)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    existing_tables = inspector.get_table_names()

    if "categories" not in existing_tables:
        return

    existing_columns = {c["name"] for c in inspector.get_columns("categories")}

    if "restock_inherit" in existing_columns:
        op.drop_column("categories", "restock_inherit")
    if "restock_min" in existing_columns:
        op.drop_column("categories", "restock_min")
    if "restock_target" in existing_columns:
        op.drop_column("categories", "restock_target")
