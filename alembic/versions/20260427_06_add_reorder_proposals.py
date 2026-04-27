"""add reorder proposals workflow tables

Revision ID: 20260427_06
Revises: 20260427_05
Create Date: 2026-04-27 12:31:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260427_06"
down_revision: Union[str, Sequence[str], None] = "20260427_05"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "reorder_proposals" not in tables:
        op.create_table(
            "reorder_proposals",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="pending"),
            sa.Column("note", sa.String(length=255), nullable=False, server_default=""),
            sa.Column("created_by", sa.String(length=120), nullable=False),
            sa.Column("reviewed_by", sa.String(length=120), nullable=False, server_default=""),
            sa.Column("rejection_reason", sa.String(length=255), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_reorder_proposals_id", "reorder_proposals", ["id"], unique=False)

    if "reorder_proposal_items" not in tables:
        op.create_table(
            "reorder_proposal_items",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column(
                "proposal_id",
                sa.Integer(),
                sa.ForeignKey("reorder_proposals.id"),
                nullable=False,
            ),
            sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
            sa.Column("warehouse_id", sa.Integer(), sa.ForeignKey("warehouses.id"), nullable=False),
            sa.Column("quantity_before", sa.Integer(), nullable=False),
            sa.Column("quantity_added", sa.Integer(), nullable=False),
            sa.Column("quantity_after", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_reorder_proposal_items_id", "reorder_proposal_items", ["id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "reorder_proposal_items" in tables:
        op.drop_index("ix_reorder_proposal_items_id", table_name="reorder_proposal_items")
        op.drop_table("reorder_proposal_items")
    if "reorder_proposals" in tables:
        op.drop_index("ix_reorder_proposals_id", table_name="reorder_proposals")
        op.drop_table("reorder_proposals")
