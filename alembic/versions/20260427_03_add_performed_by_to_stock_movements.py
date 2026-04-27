"""add performed_by column to stock_movements

Revision ID: 20260427_03
Revises: 20260427_02
Create Date: 2026-04-27 11:24:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260427_03"
down_revision: Union[str, Sequence[str], None] = "20260427_02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("stock_movements")}
    if "performed_by" not in cols:
        op.add_column(
            "stock_movements",
            sa.Column("performed_by", sa.String(length=120), nullable=False, server_default="system"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("stock_movements")}
    if "performed_by" in cols:
        op.drop_column("stock_movements", "performed_by")
