from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Integer, String, Text, func
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

    `xp` is the source of truth; level is derived via `level_for_xp`. Achievement
    and unlock tables land with WL-5.4 when something first reads them."""

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
