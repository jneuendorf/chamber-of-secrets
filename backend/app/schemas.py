from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, computed_field, field_validator, model_validator

from app.models import level_for_xp

# --- Categories ---


class CategoryCreate(BaseModel):
    name: str
    parent_id: int | None = None
    icon: str | None = None
    restock_target: float | None = None
    restock_min: float | None = None
    restock_inherit: bool = True

    @field_validator("restock_target", "restock_min")
    @classmethod
    def validate_non_negative(cls, value: float | None) -> float | None:
        if value is not None and value < 0:
            raise ValueError("must be >= 0")
        return value

    @model_validator(mode="after")
    def validate_target_min_relationship(self) -> CategoryCreate:
        if (
            self.restock_target is not None
            and self.restock_min is not None
            and self.restock_target < self.restock_min
        ):
            raise ValueError("restock_target must be >= restock_min")
        return self


class CategoryUpdate(BaseModel):
    name: str | None = None
    parent_id: int | None = None
    icon: str | None = None
    restock_target: float | None = None
    restock_min: float | None = None
    restock_inherit: bool | None = None

    @field_validator("restock_target", "restock_min")
    @classmethod
    def validate_non_negative(cls, value: float | None) -> float | None:
        if value is not None and value < 0:
            raise ValueError("must be >= 0")
        return value

    @model_validator(mode="after")
    def validate_target_min_relationship(self) -> CategoryUpdate:
        if (
            self.restock_target is not None
            and self.restock_min is not None
            and self.restock_target < self.restock_min
        ):
            raise ValueError("restock_target must be >= restock_min")
        return self


class CategoryRead(BaseModel):
    id: int
    name: str
    parent_id: int | None
    icon: str | None = None
    restock_target: float | None = None
    restock_min: float | None = None
    restock_inherit: bool = True

    model_config = {"from_attributes": True}


# --- Products ---


class ProductCreate(BaseModel):
    ean: str | None = None
    name: str
    brand: str | None = None
    category_id: int | None = None
    image_url: str | None = None


class ProductUpdate(BaseModel):
    category_id: int | None = None
    image_url: str | None = None


class ProductRead(BaseModel):
    id: int
    ean: str | None
    name: str
    brand: str | None
    category_id: int | None
    image_url: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProductWithStock(ProductRead):
    stock: float
    # No default: the key is always serialized (possibly null), and a default
    # would tell the generated client it may be absent.
    category: CategoryRead | None


class ProductMerge(BaseModel):
    source_id: int
    target_id: int

    @model_validator(mode="after")
    def validate_distinct(self) -> ProductMerge:
        if self.source_id == self.target_id:
            raise ValueError("source_id and target_id must differ")
        return self


class ProductRevisionRead(BaseModel):
    id: int
    product_id: int
    name: str
    brand: str | None
    image_url: str | None
    superseded_at: datetime

    model_config = {"from_attributes": True}


# --- Transactions ---


class TransactionCreate(BaseModel):
    product_id: int
    profile_id: int | None = None
    type: Literal["in", "out"]
    quantity: float = 1.0
    unit_price: float | None = None
    notes: str | None = None

    @field_validator("quantity")
    @classmethod
    def validate_positive_quantity(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("quantity must be > 0")
        return value


class TransactionUpdate(BaseModel):
    type: Literal["in", "out"] | None = None
    quantity: float | None = None
    unit_price: float | None = None
    notes: str | None = None

    @field_validator("quantity")
    @classmethod
    def validate_positive_quantity(cls, value: float | None) -> float | None:
        if value is not None and value <= 0:
            raise ValueError("quantity must be > 0")
        return value


class TransactionRead(BaseModel):
    id: int
    product_id: int
    profile_id: int | None
    type: Literal["in", "out"]
    quantity: float
    unit_price: float | None
    transacted_at: datetime
    notes: str | None

    model_config = {"from_attributes": True}


# --- Profiles ---


class AvatarConfig(BaseModel):
    """Layered-SVG avatar config (WL-5.1).

    `base` is a stable part id ("fox") — never a glyph or SVG markup; the art is
    resolved client-side, so parts can be redrawn without touching stored data.
    Extra keys are allowed so a newer client can round-trip parts this version
    doesn't know about (WL-5.4 adds `layers: [{slot, part}]`).
    """

    base: str | None = None
    color: str | None = None

    model_config = {"extra": "allow"}


class ProfileCreate(BaseModel):
    name: str
    avatar_config: AvatarConfig = Field(default_factory=AvatarConfig)
    locale: str | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("name must not be empty")
        return value


class ProfileUpdate(BaseModel):
    name: str | None = None
    avatar_config: AvatarConfig | None = None
    locale: str | None = None
    is_archived: bool | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("name must not be empty")
        return value


class ProfileRead(BaseModel):
    id: int
    name: str
    avatar_config: AvatarConfig
    xp: int
    current_streak: int
    longest_streak: int
    last_active_on: date | None
    locale: str | None
    is_archived: bool
    created_at: datetime
    # Earned badge keys, oldest first (WL-5.4). Names and art are client-side.
    achievements: list[str]
    # Reward-tier ids this profile has marked redeemed (WL-5.4).
    redeemed_rewards: list[int]

    model_config = {"from_attributes": True}

    @field_validator("achievements", mode="before")
    @classmethod
    def unwrap_achievements(cls, value: object) -> object:
        """Accept the ORM relationship (rows) as well as a plain list of keys."""
        if isinstance(value, list):
            return [getattr(item, "achievement_key", item) for item in value]
        return value

    @field_validator("redeemed_rewards", mode="before")
    @classmethod
    def unwrap_redeemed_rewards(cls, value: object) -> object:
        """Accept the ORM relationship (rows) as well as a plain list of ids."""
        if isinstance(value, list):
            return [getattr(item, "reward_tier_id", item) for item in value]
        return value

    @computed_field
    @property
    def level(self) -> int:
        return level_for_xp(self.xp)


# --- Reward Tiers ---


class RewardTierCreate(BaseModel):
    level: int
    description: str

    @field_validator("level")
    @classmethod
    def validate_level(cls, value: int) -> int:
        # Everyone starts at level 1, so a reward there rewards nothing.
        if value < 2:
            raise ValueError("level must be >= 2")
        return value

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("description must not be empty")
        return value


class RewardTierRead(BaseModel):
    id: int
    level: int
    description: str

    model_config = {"from_attributes": True}


# --- EAN Lookup ---


class EANLookupResult(BaseModel):
    ean: str
    # No defaults: every construction site passes these explicitly and they're
    # always serialized, so a default would misreport them as optional.
    name: str | None
    brand: str | None
    image_url: str | None
    category: str | None
    from_cache: bool = False


# --- Analytics ---


class SpendingByCategory(BaseModel):
    category: str
    total_spent: float
    item_count: int


class TimeseriesPoint(BaseModel):
    date: str  # "YYYY-MM-DD"
    category: str
    item_count: int
    total_spent: float


class RestockOverviewRow(BaseModel):
    id: int
    name: str
    brand: str | None
    category_id: int | None
    category_name: str
    current_stock: float
    effective_target: float | None
    effective_min: float | None
    resolved_from_category_id: int | None
    missing_to_target: float
    below_min: bool
    needs_restock: bool


class RestockGroupTotal(BaseModel):
    category_id: int | None
    category_name: str
    total_missing_to_target: float
    affected_products: int


class RestockOverviewResponse(BaseModel):
    rows: list[RestockOverviewRow]
    total_missing_quantity: float
    total_products_needing_restock: int
    by_child_category: list[RestockGroupTotal]
    by_parent_category: list[RestockGroupTotal]
