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
    reorder_level: int = Field(default=0, ge=0)
    reorder_quantity: int = Field(default=0, ge=0)


class ProductOut(BaseModel):
    id: int
    sku: str
    name: str
    quantity_on_hand: int
    reorder_level: int
    reorder_quantity: int
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
    performed_by: str
    created_at: datetime

    class Config:
        from_attributes = True


class InventoryLotOut(BaseModel):
    id: int
    product_id: int
    quantity_remaining: int
    created_at: datetime

    class Config:
        from_attributes = True


class StockTransferCreate(BaseModel):
    source_product_id: int
    destination_product_id: int
    quantity: int = Field(gt=0)
    note: str = ""


class StockTransferOut(BaseModel):
    id: int
    source_product_id: int
    destination_product_id: int
    source_warehouse_id: int
    destination_warehouse_id: int
    quantity: int
    note: str
    performed_by: str
    created_at: datetime

    class Config:
        from_attributes = True


class LowStockAlertOut(BaseModel):
    product_id: int
    sku: str
    name: str
    warehouse_id: int
    warehouse_name: str
    quantity_on_hand: int
    reorder_level: int
    reorder_quantity: int
    suggested_reorder: int
