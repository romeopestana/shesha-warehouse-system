"""add reorder fields to products for low-stock alerts

Revision ID: 20260427_05
Revises: 20260427_04
Create Date: 2026-04-27 12:17:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260427_05"
down_revision: Union[str, Sequence[str], None] = "20260427_04"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("products")}
    if "reorder_level" not in cols:
        op.add_column(
            "products",
            sa.Column("reorder_level", sa.Integer(), nullable=False, server_default="0"),
        )
    if "reorder_quantity" not in cols:
        op.add_column(
            "products",
            sa.Column("reorder_quantity", sa.Integer(), nullable=False, server_default="0"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("products")}
    if "reorder_quantity" in cols:
        op.drop_column("products", "reorder_quantity")
    if "reorder_level" in cols:
        op.drop_column("products", "reorder_level")
