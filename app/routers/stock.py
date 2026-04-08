from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import User, require_roles
from app.database import get_db
from app.models import Product, StockMovement
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

    if payload.movement_type == "OUT" and product.quantity_on_hand < payload.quantity:
        raise HTTPException(status_code=400, detail="Insufficient stock")

    if payload.movement_type == "IN":
        product.quantity_on_hand += payload.quantity
    else:
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
