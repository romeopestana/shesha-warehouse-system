"""baseline revision compatibility marker

Revision ID: 20260408_01
Revises:
Create Date: 2026-04-27 11:00:00
"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "20260408_01"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Baseline marker only; existing schema already present in current environments.
    pass


def downgrade() -> None:
    pass
