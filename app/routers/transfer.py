from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth import User, require_roles
from app.database import get_db
from app.models import InventoryLot, Product, StockMovement, StockTransfer
from app.schemas import StockTransferCreate, StockTransferOut

router = APIRouter(prefix="/stock-transfers", tags=["stock-transfers"])


def _consume_fifo_lots(db: Session, product: Product, quantity: int) -> None:
    lots = (
        db.query(InventoryLot)
        .filter(
            InventoryLot.product_id == product.id,
            InventoryLot.quantity_remaining > 0,
        )
        .order_by(InventoryLot.created_at.asc(), InventoryLot.id.asc())
        .all()
    )

    # Backfill a single lot for legacy stock that predates FIFO lots.
    if not lots and product.quantity_on_hand > 0:
        legacy_lot = InventoryLot(
            product_id=product.id,
            quantity_remaining=product.quantity_on_hand,
        )
        db.add(legacy_lot)
        db.flush()
        lots = [legacy_lot]

    remaining_to_consume = quantity
    for lot in lots:
        if remaining_to_consume <= 0:
            break
        take = min(lot.quantity_remaining, remaining_to_consume)
        lot.quantity_remaining -= take
        remaining_to_consume -= take

    if remaining_to_consume > 0:
        raise HTTPException(status_code=400, detail="Insufficient stock")


@router.post("", response_model=StockTransferOut)
def create_stock_transfer(
    payload: StockTransferCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    source = db.query(Product).filter(Product.id == payload.source_product_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source product not found")

    destination = db.query(Product).filter(Product.id == payload.destination_product_id).first()
    if not destination:
        raise HTTPException(status_code=404, detail="Destination product not found")

    if source.id == destination.id:
        raise HTTPException(status_code=400, detail="Source and destination products must differ")

    if source.warehouse_id == destination.warehouse_id:
        raise HTTPException(status_code=400, detail="Source and destination warehouses must differ")

    if source.quantity_on_hand < payload.quantity:
        raise HTTPException(status_code=400, detail="Insufficient stock")

    _consume_fifo_lots(db, source, payload.quantity)

    source.quantity_on_hand -= payload.quantity
    destination.quantity_on_hand += payload.quantity
    db.add(
        InventoryLot(
            product_id=destination.id,
            quantity_remaining=payload.quantity,
        )
    )

    transfer = StockTransfer(
        source_product_id=source.id,
        destination_product_id=destination.id,
        source_warehouse_id=source.warehouse_id,
        destination_warehouse_id=destination.warehouse_id,
        quantity=payload.quantity,
        note=payload.note,
        performed_by=current_user.username,
    )
    db.add(transfer)

    # Keep existing stock movement audit history aligned with transfers.
    db.add(
        StockMovement(
            product_id=source.id,
            movement_type="OUT",
            quantity=payload.quantity,
            note=f"TRANSFER_OUT:{destination.id} {payload.note}".strip(),
            performed_by=current_user.username,
        )
    )
    db.add(
        StockMovement(
            product_id=destination.id,
            movement_type="IN",
            quantity=payload.quantity,
            note=f"TRANSFER_IN:{source.id} {payload.note}".strip(),
            performed_by=current_user.username,
        )
    )

    db.add(source)
    db.add(destination)
    db.commit()
    db.refresh(transfer)
    return transfer


@router.get("", response_model=list[StockTransferOut])
def list_stock_transfers(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "clerk")),
    source_warehouse_id: int | None = Query(default=None),
    destination_warehouse_id: int | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
):
    query = db.query(StockTransfer)

    if source_warehouse_id is not None:
        query = query.filter(StockTransfer.source_warehouse_id == source_warehouse_id)
    if destination_warehouse_id is not None:
        query = query.filter(StockTransfer.destination_warehouse_id == destination_warehouse_id)
    if date_from is not None:
        query = query.filter(StockTransfer.created_at >= date_from)
    if date_to is not None:
        query = query.filter(StockTransfer.created_at <= date_to)

    return query.order_by(StockTransfer.id.desc()).all()
