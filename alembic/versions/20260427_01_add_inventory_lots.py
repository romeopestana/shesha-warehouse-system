"""add inventory_lots table for FIFO stock tracking

Revision ID: 20260427_01
Revises:
Create Date: 2026-04-27 10:45:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260427_01"
down_revision: Union[str, Sequence[str], None] = "20260408_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("inventory_lots"):
        op.create_table(
            "inventory_lots",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
            sa.Column("quantity_remaining", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_inventory_lots_id", "inventory_lots", ["id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("inventory_lots"):
        op.drop_index("ix_inventory_lots_id", table_name="inventory_lots")
        op.drop_table("inventory_lots")
