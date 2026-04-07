from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class WarehouseCreate(BaseModel):
    name: str
    location: str


class WarehouseOut(BaseModel):
    id: int
    name: str
    location: str
    created_at: datetime

    class Config:
        from_attributes = True


class ProductCreate(BaseModel):
    sku: str
    name: str
    warehouse_id: int
    quantity_on_hand: int = 0


class ProductOut(BaseModel):
    id: int
    sku: str
    name: str
    quantity_on_hand: int
    warehouse_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class StockMovementCreate(BaseModel):
    product_id: int
    movement_type: Literal["IN", "OUT"]
    quantity: int = Field(gt=0)
    note: str = ""


class StockMovementOut(BaseModel):
    id: int
    product_id: int
    movement_type: str
    quantity: int
    note: str
    created_at: datetime

    class Config:
        from_attributes = True
