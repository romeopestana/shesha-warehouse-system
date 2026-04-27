"""add stock_transfers table for warehouse transfers

Revision ID: 20260427_04
Revises: 20260427_03
Create Date: 2026-04-27 12:05:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260427_04"
down_revision: Union[str, Sequence[str], None] = "20260427_03"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("stock_transfers"):
        op.create_table(
            "stock_transfers",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("source_product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
            sa.Column("destination_product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
            sa.Column("source_warehouse_id", sa.Integer(), sa.ForeignKey("warehouses.id"), nullable=False),
            sa.Column("destination_warehouse_id", sa.Integer(), sa.ForeignKey("warehouses.id"), nullable=False),
            sa.Column("quantity", sa.Integer(), nullable=False),
            sa.Column("note", sa.String(length=255), nullable=False, server_default=""),
            sa.Column("performed_by", sa.String(length=120), nullable=False, server_default="system"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_stock_transfers_id", "stock_transfers", ["id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("stock_transfers"):
        op.drop_index("ix_stock_transfers_id", table_name="stock_transfers")
        op.drop_table("stock_transfers")
