"""add job_runs table for scheduled scan idempotency

Revision ID: 20260427_08
Revises: 20260427_07
Create Date: 2026-04-27 12:52:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260427_08"
down_revision: Union[str, Sequence[str], None] = "20260427_07"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("job_runs"):
        op.create_table(
            "job_runs",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("job_name", sa.String(length=80), nullable=False),
            sa.Column("run_date", sa.String(length=20), nullable=False),
            sa.Column("warehouse_id", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="completed"),
            sa.Column("details", sa.String(length=255), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_job_runs_id", "job_runs", ["id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("job_runs"):
        op.drop_index("ix_job_runs_id", table_name="job_runs")
        op.drop_table("job_runs")
