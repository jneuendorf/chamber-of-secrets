"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-03-09

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect

from alembic import op

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
            sa.Column("restock_target", sa.Float(), nullable=True),
            sa.Column("restock_min", sa.Float(), nullable=True),
            sa.Column("restock_inherit", sa.Boolean(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
    else:
        cols = {c["name"] for c in inspector.get_columns("categories")}
        if "icon" not in cols:
            op.add_column("categories", sa.Column("icon", sa.Text(), nullable=True))
        if "restock_target" not in cols:
            op.add_column("categories", sa.Column("restock_target", sa.Float(), nullable=True))
        if "restock_min" not in cols:
            op.add_column("categories", sa.Column("restock_min", sa.Float(), nullable=True))
        if "restock_inherit" not in cols:
            # Add NOT NULL with a temporary server default to backfill existing
            # rows, then drop it (model uses a Python-side default only). SQLite
            # has no ALTER COLUMN, so the drop runs via a batch table rebuild.
            op.add_column(
                "categories",
                sa.Column(
                    "restock_inherit",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.true(),
                ),
            )
            with op.batch_alter_table("categories") as batch_op:
                batch_op.alter_column(
                    "restock_inherit",
                    existing_type=sa.Boolean(),
                    existing_nullable=False,
                    server_default=None,
                )

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

    # Profiles must exist before inventory_transactions references them.
    if "profiles" not in existing:
        op.create_table(
            "profiles",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(50), nullable=False),
            sa.Column("avatar_config", sa.JSON(), nullable=False),
            sa.Column("xp", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("current_streak", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("longest_streak", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("last_active_on", sa.Date(), nullable=True),
            sa.Column("locale", sa.String(5), nullable=True),
            sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    if "inventory_transactions" not in existing:
        op.create_table(
            "inventory_transactions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
            sa.Column(
                "profile_id",
                sa.Integer(),
                sa.ForeignKey("profiles.id"),
                nullable=True,
            ),
            sa.Column("type", sa.String(3), nullable=False),
            sa.Column("quantity", sa.Float(), nullable=False),
            sa.Column("unit_price", sa.Float(), nullable=True),
            sa.Column("transacted_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_inventory_transactions_profile_id",
            "inventory_transactions",
            ["profile_id"],
        )

    if "profile_achievements" not in existing:
        op.create_table(
            "profile_achievements",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("profile_id", sa.Integer(), sa.ForeignKey("profiles.id"), nullable=False),
            sa.Column("achievement_key", sa.String(50), nullable=False),
            sa.Column("earned_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("profile_id", "achievement_key"),
        )
        op.create_index(
            "ix_profile_achievements_profile_id",
            "profile_achievements",
            ["profile_id"],
        )

    if "reward_tiers" not in existing:
        op.create_table(
            "reward_tiers",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("level", sa.Integer(), nullable=False),
            sa.Column("description", sa.String(200), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_reward_tiers_level", "reward_tiers", ["level"])

    if "profile_rewards" not in existing:
        op.create_table(
            "profile_rewards",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("profile_id", sa.Integer(), sa.ForeignKey("profiles.id"), nullable=False),
            sa.Column(
                "reward_tier_id",
                sa.Integer(),
                sa.ForeignKey("reward_tiers.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("redeemed_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("profile_id", "reward_tier_id"),
        )
        op.create_index("ix_profile_rewards_profile_id", "profile_rewards", ["profile_id"])
        op.create_index("ix_profile_rewards_reward_tier_id", "profile_rewards", ["reward_tier_id"])


def downgrade() -> None:
    op.drop_index("ix_profile_rewards_reward_tier_id", table_name="profile_rewards")
    op.drop_index("ix_profile_rewards_profile_id", table_name="profile_rewards")
    op.drop_table("profile_rewards")
    op.drop_index("ix_reward_tiers_level", table_name="reward_tiers")
    op.drop_table("reward_tiers")
    op.drop_index("ix_profile_achievements_profile_id", table_name="profile_achievements")
    op.drop_table("profile_achievements")
    op.drop_index("ix_inventory_transactions_profile_id", table_name="inventory_transactions")
    op.drop_table("inventory_transactions")
    op.drop_table("profiles")
    op.drop_table("product_revisions")
    op.drop_index("ix_products_ean", table_name="products")
    op.drop_table("products")
    op.drop_table("categories")
