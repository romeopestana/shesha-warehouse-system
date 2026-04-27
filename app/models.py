from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Warehouse(Base):
    __tablename__ = "warehouses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    products: Mapped[list["Product"]] = relationship(back_populates="warehouse")


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    sku: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    quantity_on_hand: Mapped[int] = mapped_column(Integer, default=0)
    reorder_level: Mapped[int] = mapped_column(Integer, default=0)
    reorder_quantity: Mapped[int] = mapped_column(Integer, default=0)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    warehouse: Mapped["Warehouse"] = relationship(back_populates="products")
    stock_movements: Mapped[list["StockMovement"]] = relationship(back_populates="product")
    inventory_lots: Mapped[list["InventoryLot"]] = relationship(back_populates="product")


class InventoryLot(Base):
    __tablename__ = "inventory_lots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    quantity_remaining: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    product: Mapped["Product"] = relationship(back_populates="inventory_lots")


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    movement_type: Mapped[str] = mapped_column(String(10), nullable=False)  # IN or OUT
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    note: Mapped[str] = mapped_column(String(255), default="")
    performed_by: Mapped[str] = mapped_column(String(120), default="system")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    product: Mapped["Product"] = relationship(back_populates="stock_movements")


class StockTransfer(Base):
    __tablename__ = "stock_transfers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source_product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    destination_product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    source_warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"), nullable=False)
    destination_warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    note: Mapped[str] = mapped_column(String(255), default="")
    performed_by: Mapped[str] = mapped_column(String(120), default="system")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ReorderProposal(Base):
    __tablename__ = "reorder_proposals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    status: Mapped[str] = mapped_column(String(30), default="pending")
    note: Mapped[str] = mapped_column(String(255), default="")
    created_by: Mapped[str] = mapped_column(String(120), nullable=False)
    reviewed_by: Mapped[str] = mapped_column(String(120), default="")
    rejection_reason: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    items: Mapped[list["ReorderProposalItem"]] = relationship(back_populates="proposal")


class ReorderProposalItem(Base):
    __tablename__ = "reorder_proposal_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    proposal_id: Mapped[int] = mapped_column(ForeignKey("reorder_proposals.id"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"), nullable=False)
    quantity_before: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_added: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_after: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    proposal: Mapped["ReorderProposal"] = relationship(back_populates="items")


class NotificationEvent(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    message: Mapped[str] = mapped_column(String(255), nullable=False)
    related_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_read: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    read_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class JobRun(Base):
    __tablename__ = "job_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    job_name: Mapped[str] = mapped_column(String(80), nullable=False)
    run_date: Mapped[str] = mapped_column(String(20), nullable=False)
    warehouse_id: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="completed")
    details: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AppUser(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    disabled: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
