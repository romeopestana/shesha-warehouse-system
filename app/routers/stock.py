from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import User, require_roles
from app.database import get_db
from app.models import InventoryLot, Product, StockMovement
from app.schemas import StockMovementCreate, StockMovementOut

router = APIRouter(prefix="/stock-movements", tags=["stock-movements"])


@router.post("", response_model=StockMovementOut)
def create_stock_movement(
    payload: StockMovementCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin")),
):
    product = db.query(Product).filter(Product.id == payload.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if payload.movement_type == "IN":
        product.quantity_on_hand += payload.quantity
        db.add(
            InventoryLot(
                product_id=product.id,
                quantity_remaining=payload.quantity,
            )
        )
    else:
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

        remaining_to_consume = payload.quantity
        for lot in lots:
            if remaining_to_consume <= 0:
                break
            take = min(lot.quantity_remaining, remaining_to_consume)
            lot.quantity_remaining -= take
            remaining_to_consume -= take

        if remaining_to_consume > 0:
            raise HTTPException(status_code=400, detail="Insufficient stock")

        product.quantity_on_hand -= payload.quantity

    movement = StockMovement(
        product_id=payload.product_id,
        movement_type=payload.movement_type,
        quantity=payload.quantity,
        note=payload.note,
    )
    db.add(movement)
    db.add(product)
    db.commit()
    db.refresh(movement)
    return movement


@router.get("", response_model=list[StockMovementOut])
def list_stock_movements(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "clerk")),
):
    return db.query(StockMovement).order_by(StockMovement.id.desc()).all()
