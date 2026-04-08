from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Product, Warehouse


def seed(db: Session) -> None:
    warehouse = db.query(Warehouse).filter(Warehouse.name == "Main Warehouse").first()
    if warehouse is None:
        warehouse = Warehouse(name="Main Warehouse", location="Durban")
        db.add(warehouse)
        db.flush()

    product = db.query(Product).filter(Product.sku == "SKU-1001").first()
    if product is None:
        product = Product(
            sku="SKU-1001",
            name="Sample Product",
            quantity_on_hand=100,
            warehouse_id=warehouse.id,
        )
        db.add(product)

    db.commit()


def main() -> None:
    db = SessionLocal()
    try:
        seed(db)
        print("Seed complete.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
