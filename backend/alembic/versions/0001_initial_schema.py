"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-03-09

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect as sa_inspect

# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    existing = inspector.get_table_names()

    if "categories" not in existing:
        op.create_table(
            "categories",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(100), nullable=False),
            sa.Column("parent_id", sa.Integer(), sa.ForeignKey("categories.id"), nullable=True),
            sa.Column("icon", sa.Text(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
    else:
        cols = {c["name"] for c in inspector.get_columns("categories")}
        if "icon" not in cols:
            op.add_column("categories", sa.Column("icon", sa.Text(), nullable=True))

    if "products" not in existing:
        op.create_table(
            "products",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("ean", sa.String(13), nullable=True),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("brand", sa.String(255), nullable=True),
            sa.Column("category_id", sa.Integer(), sa.ForeignKey("categories.id"), nullable=True),
            sa.Column("image_url", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("ean"),
        )
        op.create_index("ix_products_ean", "products", ["ean"])

    if "product_revisions" not in existing:
        op.create_table(
            "product_revisions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("brand", sa.String(255), nullable=True),
            sa.Column("image_url", sa.Text(), nullable=True),
            sa.Column("superseded_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    if "inventory_transactions" not in existing:
        op.create_table(
            "inventory_transactions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
            sa.Column("type", sa.String(3), nullable=False),
            sa.Column("quantity", sa.Float(), nullable=False),
            sa.Column("unit_price", sa.Float(), nullable=True),
            sa.Column("transacted_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )


def downgrade() -> None:
    op.drop_table("inventory_transactions")
    op.drop_table("product_revisions")
    op.drop_index("ix_products_ean", table_name="products")
    op.drop_table("products")
    op.drop_table("categories")
