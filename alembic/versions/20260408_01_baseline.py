"""baseline revision compatibility marker

Revision ID: 20260408_01
Revises:
Create Date: 2026-04-27 11:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260408_01"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    # Fresh databases (e.g. CI) do not have pre-baseline tables, so create them.
    if "warehouses" not in existing_tables:
        op.create_table(
            "warehouses",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("name", sa.String(length=120), nullable=False, unique=True),
            sa.Column("location", sa.String(length=255), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_warehouses_id", "warehouses", ["id"], unique=False)

    if "products" not in existing_tables:
        op.create_table(
            "products",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("sku", sa.String(length=80), nullable=False, unique=True),
            sa.Column("name", sa.String(length=160), nullable=False),
            sa.Column("quantity_on_hand", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("warehouse_id", sa.Integer(), sa.ForeignKey("warehouses.id"), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_products_id", "products", ["id"], unique=False)

    if "stock_movements" not in existing_tables:
        op.create_table(
            "stock_movements",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
            sa.Column("movement_type", sa.String(length=10), nullable=False),
            sa.Column("quantity", sa.Integer(), nullable=False),
            sa.Column("note", sa.String(length=255), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_stock_movements_id", "stock_movements", ["id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "stock_movements" in existing_tables:
        op.drop_index("ix_stock_movements_id", table_name="stock_movements")
        op.drop_table("stock_movements")
    if "products" in existing_tables:
        op.drop_index("ix_products_id", table_name="products")
        op.drop_table("products")
    if "warehouses" in existing_tables:
        op.drop_index("ix_warehouses_id", table_name="warehouses")
        op.drop_table("warehouses")
