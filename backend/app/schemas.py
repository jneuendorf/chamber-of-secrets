from datetime import datetime
from typing import Literal

from pydantic import BaseModel

# --- Categories ---


class CategoryCreate(BaseModel):
    name: str
    parent_id: int | None = None
    icon: str | None = None


class CategoryUpdate(BaseModel):
    icon: str | None = None


class CategoryRead(BaseModel):
    id: int
    name: str
    parent_id: int | None
    icon: str | None = None

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
