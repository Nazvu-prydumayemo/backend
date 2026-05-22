"""Remove working_hours column (replaced by CourtSchedule table)

Revision ID: a3b4c5d6e7f8
Revises: a1b2c3d4e5f6, b7c8d9e0f1a2
Create Date: 2026-05-22 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a3b4c5d6e7f8"
down_revision: Union[str, Sequence[str], None] = ["a1b2c3d4e5f6", "b7c8d9e0f1a2"]
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove working_hours column."""
    op.drop_column("courts", "working_hours")


def downgrade() -> None:
    """Restore working_hours column."""
    op.add_column("courts", sa.Column("working_hours", sa.String(), nullable=True))
