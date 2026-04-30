from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import User, require_roles
from app.database import get_db
from app.models import Product, Warehouse
from app.notifications import emit_notification
from app.schemas import LowStockAlertOut, LowStockSummaryOut, LowStockWarehouseSummary

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("/low-stock", response_model=list[LowStockAlertOut])
def list_low_stock_alerts(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "clerk")),
    warehouse_id: int | None = Query(default=None),
):
    query = db.query(Product, Warehouse).join(Warehouse, Product.warehouse_id == Warehouse.id)
    query = query.filter(Product.quantity_on_hand <= Product.reorder_level)

    if warehouse_id is not None:
        query = query.filter(Product.warehouse_id == warehouse_id)

    rows = query.order_by(Product.quantity_on_hand.asc(), Product.id.asc()).all()
    emit_notification(
        db=db,
        event_type="low_stock_observed",
        message=f"Low-stock alerts viewed ({len(rows)} items)",
        related_id=warehouse_id,
    )
    db.commit()
    return [
        LowStockAlertOut(
            product_id=product.id,
            sku=product.sku,
            name=product.name,
            warehouse_id=warehouse.id,
            warehouse_name=warehouse.name,
            quantity_on_hand=product.quantity_on_hand,
            reorder_level=product.reorder_level,
            reorder_quantity=product.reorder_quantity,
            suggested_reorder=max(product.reorder_quantity, product.reorder_level - product.quantity_on_hand),
        )
        for product, warehouse in rows
    ]


@router.get("/summary", response_model=LowStockSummaryOut)
def low_stock_summary(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "clerk")),
):
    rows = (
        db.query(
            Warehouse.id.label("warehouse_id"),
            Warehouse.name.label("warehouse_name"),
            func.count(Product.id).label("low_stock_count"),
        )
        .join(Product, Product.warehouse_id == Warehouse.id)
        .filter(Product.quantity_on_hand <= Product.reorder_level)
        .group_by(Warehouse.id, Warehouse.name)
        .order_by(Warehouse.name.asc())
        .all()
    )
    return LowStockSummaryOut(
        total_low_stock_items=sum(int(row.low_stock_count) for row in rows),
        warehouse_breakdown=[
            LowStockWarehouseSummary(
                warehouse_id=int(row.warehouse_id),
                warehouse_name=str(row.warehouse_name),
                low_stock_count=int(row.low_stock_count),
            )
            for row in rows
        ],
    )
