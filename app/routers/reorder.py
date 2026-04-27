from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import User, require_roles
from app.database import get_db
from app.models import InventoryLot, Product, StockMovement
from app.schemas import (
    SuggestedReorderCreate,
    SuggestedReorderCreatedItem,
    SuggestedReorderResult,
    SuggestedReorderSkippedItem,
)

router = APIRouter(prefix="/reorders", tags=["reorders"])


@router.post("/suggested", response_model=SuggestedReorderResult)
def create_suggested_reorders(
    payload: SuggestedReorderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    query = db.query(Product).filter(Product.quantity_on_hand <= Product.reorder_level)

    if payload.warehouse_id is not None:
        query = query.filter(Product.warehouse_id == payload.warehouse_id)
    if payload.product_ids:
        query = query.filter(Product.id.in_(payload.product_ids))

    products = query.order_by(Product.id.asc()).all()
    created: list[SuggestedReorderCreatedItem] = []
    skipped: list[SuggestedReorderSkippedItem] = []

    for product in products:
        if product.reorder_quantity <= 0:
            skipped.append(
                SuggestedReorderSkippedItem(
                    product_id=product.id,
                    reason="reorder_quantity is 0",
                )
            )
            continue

        before = product.quantity_on_hand
        product.quantity_on_hand += product.reorder_quantity
        db.add(
            InventoryLot(
                product_id=product.id,
                quantity_remaining=product.reorder_quantity,
            )
        )
        db.add(
            StockMovement(
                product_id=product.id,
                movement_type="IN",
                quantity=product.reorder_quantity,
                note=payload.note,
                performed_by=current_user.username,
            )
        )
        db.add(product)
        created.append(
            SuggestedReorderCreatedItem(
                product_id=product.id,
                quantity_added=product.reorder_quantity,
                quantity_before=before,
                quantity_after=product.quantity_on_hand,
                warehouse_id=product.warehouse_id,
            )
        )

    db.commit()
    return SuggestedReorderResult(created=created, skipped=skipped)
