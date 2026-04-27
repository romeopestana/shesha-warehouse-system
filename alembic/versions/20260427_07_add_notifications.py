"""add notifications table for in-app events

Revision ID: 20260427_07
Revises: 20260427_06
Create Date: 2026-04-27 12:45:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260427_07"
down_revision: Union[str, Sequence[str], None] = "20260427_06"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("notifications"):
        op.create_table(
            "notifications",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("event_type", sa.String(length=80), nullable=False),
            sa.Column("message", sa.String(length=255), nullable=False),
            sa.Column("related_id", sa.Integer(), nullable=True),
            sa.Column("is_read", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("read_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_notifications_id", "notifications", ["id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("notifications"):
        op.drop_index("ix_notifications_id", table_name="notifications")
        op.drop_table("notifications")
