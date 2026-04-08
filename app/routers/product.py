from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import InventoryLot, Product, Warehouse
from app.schemas import ProductCreate, ProductOut

router = APIRouter(prefix="/products", tags=["products"])


@router.post("", response_model=ProductOut)
def create_product(payload: ProductCreate, db: Session = Depends(get_db)):
    # Ensure the FIFO lot table exists even without migration tooling.
    InventoryLot.__table__.create(bind=db.get_bind(), checkfirst=True)

    warehouse = db.query(Warehouse).filter(Warehouse.id == payload.warehouse_id).first()
    if not warehouse:
        raise HTTPException(status_code=404, detail="Warehouse not found")

    existing = db.query(Product).filter(Product.sku == payload.sku).first()
    if existing:
        raise HTTPException(status_code=400, detail="SKU already exists")

    product = Product(
        sku=payload.sku,
        name=payload.name,
        warehouse_id=payload.warehouse_id,
        quantity_on_hand=payload.quantity_on_hand,
    )
    db.add(product)
    db.flush()

    if payload.quantity_on_hand > 0:
        db.add(
            InventoryLot(
                product_id=product.id,
                quantity_remaining=payload.quantity_on_hand,
            )
        )

    db.commit()
    db.refresh(product)
    return product


@router.get("", response_model=list[ProductOut])
def list_products(db: Session = Depends(get_db)):
    return db.query(Product).order_by(Product.id.asc()).all()
