from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def level_for_xp(xp: int) -> int:
    """Level derived from XP (never stored). 100 XP → L2, 400 → L3, 900 → L4 …
    # ponytail: quadratic curve, retune the 100 constant when WL-5.3 balances XP."""
    return int((max(xp, 0) / 100) ** 0.5) + 1


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"))
    icon: Mapped[str | None] = mapped_column(Text, nullable=True)
    restock_target: Mapped[float | None] = mapped_column(nullable=True)
    restock_min: Mapped[float | None] = mapped_column(nullable=True)
    restock_inherit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    parent: Mapped[Category | None] = relationship(
        "Category",
        remote_side="Category.id",
        back_populates="children",
    )
    children: Mapped[list[Category]] = relationship("Category", back_populates="parent")
    products: Mapped[list[Product]] = relationship(back_populates="category")


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    ean: Mapped[str | None] = mapped_column(String(13), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    brand: Mapped[str | None] = mapped_column(String(255))
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"))
    image_url: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
    )

    category: Mapped[Category | None] = relationship(back_populates="products")
    transactions: Mapped[list[InventoryTransaction]] = relationship(back_populates="product")
    revisions: Mapped[list[ProductRevision]] = relationship(
        back_populates="product",
        order_by="ProductRevision.superseded_at.desc()",
    )


class ProductRevision(Base):
    """Immutable snapshot of a product's fields before each refresh or manual edit."""

    __tablename__ = "product_revisions"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    brand: Mapped[str | None] = mapped_column(String(255))
    image_url: Mapped[str | None] = mapped_column(Text)
    superseded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    product: Mapped[Product] = relationship(back_populates="revisions")


class InventoryTransaction(Base):
    __tablename__ = "inventory_transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    profile_id: Mapped[int | None] = mapped_column(
        ForeignKey("profiles.id"),
        index=True,
    )  # NULL = no profile selected / legacy
    type: Mapped[str] = mapped_column(String(3), nullable=False)  # 'in' or 'out'
    quantity: Mapped[float] = mapped_column(nullable=False, default=1.0)
    unit_price: Mapped[float | None] = mapped_column()
    transacted_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    notes: Mapped[str | None] = mapped_column(Text)

    product: Mapped[Product] = relationship(back_populates="transactions")


class Profile(Base):
    """Lightweight, login-less identity for per-profile gamification (WL-5.1).

    `xp` is the source of truth; level is derived via `level_for_xp`. `ProfileUnlock`
    (owned cosmetics) still waits for the avatar compositor to read it."""

    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    avatar_config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    xp: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    current_streak: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    longest_streak: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_active_on: Mapped[date | None] = mapped_column(Date)
    locale: Mapped[str | None] = mapped_column(String(5))
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    achievements: Mapped[list[ProfileAchievement]] = relationship(
        back_populates="profile",
        lazy="selectin",
        order_by="ProfileAchievement.earned_at",
    )
    redeemed_rewards: Mapped[list[ProfileReward]] = relationship(
        back_populates="profile",
        lazy="selectin",
        order_by="ProfileReward.redeemed_at",
    )


class ProfileAchievement(Base):
    """One earned badge (WL-5.4). Rows are append-only — a badge is never unearned.

    Stores the catalog **key** only; name, description and art are resolved
    client-side, so a badge can be renamed or redrawn without a migration."""

    __tablename__ = "profile_achievements"
    __table_args__ = (UniqueConstraint("profile_id", "achievement_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id"), nullable=False, index=True)
    achievement_key: Mapped[str] = mapped_column(String(50), nullable=False)
    earned_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    profile: Mapped[Profile] = relationship(back_populates="achievements")


class RewardTier(Base):
    """A real-life reward a household grants when a profile reaches `level` (WL-5.4).

    Household-wide, not per profile: whoever reaches the level unlocks it. Multiple
    rows may share a level. Unlocking is *derived* (level >= tier.level); the one
    per-profile bit that is stored is redemption — see `ProfileReward`."""

    __tablename__ = "reward_tiers"

    id: Mapped[int] = mapped_column(primary_key=True)
    level: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ProfileReward(Base):
    """A reward a profile has marked redeemed in real life (WL-5.4).

    Per profile, unlike the household-wide `RewardTier` it points at: each kid
    checks off their own treat. The row's *presence* is the redeemed flag —
    un-redeeming deletes it. Deleting a tier cascades its redemptions.

    Whose tap this is isn't enforced server-side: profiles are login-less
    (WL-5.1), so "only redeem your own" is a client guard, not access control.
    The redeem endpoint still validates the reward is actually unlocked."""

    __tablename__ = "profile_rewards"
    __table_args__ = (UniqueConstraint("profile_id", "reward_tier_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id"), nullable=False, index=True)
    reward_tier_id: Mapped[int] = mapped_column(
        ForeignKey("reward_tiers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    redeemed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    profile: Mapped[Profile] = relationship(back_populates="redeemed_rewards")
