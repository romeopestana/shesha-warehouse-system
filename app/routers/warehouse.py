from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Warehouse
from app.schemas import WarehouseCreate, WarehouseOut

router = APIRouter(prefix="/warehouses", tags=["warehouses"])


@router.post("", response_model=WarehouseOut)
def create_warehouse(payload: WarehouseCreate, db: Session = Depends(get_db)):
    exists = db.query(Warehouse).filter(Warehouse.name == payload.name).first()
    if exists:
        raise HTTPException(status_code=400, detail="Warehouse name already exists")

    warehouse = Warehouse(name=payload.name, location=payload.location)
    db.add(warehouse)
    db.commit()
    db.refresh(warehouse)
    return warehouse


@router.get("", response_model=list[WarehouseOut])
def list_warehouses(db: Session = Depends(get_db)):
    return db.query(Warehouse).order_by(Warehouse.id.asc()).all()
