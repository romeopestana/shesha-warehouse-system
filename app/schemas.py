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


class SuggestedReorderCreate(BaseModel):
    warehouse_id: int | None = None
    product_ids: list[int] | None = None
    note: str = "Automated reorder from low-stock alerts"
    dry_run: bool = False


class SuggestedReorderCreatedItem(BaseModel):
    product_id: int
    quantity_added: int
    quantity_before: int
    quantity_after: int
    warehouse_id: int


class SuggestedReorderSkippedItem(BaseModel):
    product_id: int
    reason: str


class SuggestedReorderResult(BaseModel):
    proposal_id: int | None = None
    created: list[SuggestedReorderCreatedItem]
    skipped: list[SuggestedReorderSkippedItem]


class ReorderProposalItemOut(BaseModel):
    id: int
    product_id: int
    warehouse_id: int
    quantity_before: int
    quantity_added: int
    quantity_after: int
    created_at: datetime

    class Config:
        from_attributes = True


class ReorderProposalOut(BaseModel):
    id: int
    status: str
    note: str
    created_by: str
    reviewed_by: str
    rejection_reason: str
    created_at: datetime
    reviewed_at: datetime | None = None
    items: list[ReorderProposalItemOut]

    class Config:
        from_attributes = True


class ReorderProposalRejectRequest(BaseModel):
    reason: str = Field(min_length=1)


class ReorderApprovalBlockedItem(BaseModel):
    item_id: int
    product_id: int
    reason: str


class ReorderApprovalAppliedItem(BaseModel):
    item_id: int
    product_id: int
    quantity_added: int


class ReorderProposalApprovalResult(BaseModel):
    proposal: ReorderProposalOut
    applied: list[ReorderApprovalAppliedItem]
    blocked: list[ReorderApprovalBlockedItem]


class NotificationOut(BaseModel):
    id: int
    event_type: str
    message: str
    related_id: int | None = None
    is_read: int
    created_at: datetime
    read_at: datetime | None = None

    class Config:
        from_attributes = True


class DailyReorderScanOut(BaseModel):
    run_date: str
    warehouses_scanned: int
    proposals_created: int
    skipped_existing_runs: int
    proposal_ids: list[int]
    auto_approved_ids: list[int]
    pending_ids: list[int]
