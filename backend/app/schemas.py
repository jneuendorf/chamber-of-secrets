from datetime import datetime
from typing import Literal

from pydantic import BaseModel, field_validator, model_validator

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
    def validate_target_min_relationship(self) -> "CategoryCreate":
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
    def validate_target_min_relationship(self) -> "CategoryUpdate":
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
    category: CategoryRead | None = None


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
    type: Literal["in", "out"]
    quantity: float = 1.0
    unit_price: float | None = None
    notes: str | None = None


class TransactionRead(BaseModel):
    id: int
    product_id: int
    type: str
    quantity: float
    unit_price: float | None
    transacted_at: datetime
    notes: str | None

    model_config = {"from_attributes": True}


# --- EAN Lookup ---


class EANLookupResult(BaseModel):
    ean: str
    name: str | None = None
    brand: str | None = None
    image_url: str | None = None
    category: str | None = None
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
