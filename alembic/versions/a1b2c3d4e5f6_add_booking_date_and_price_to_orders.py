"""Add booking_date and total_price to orders table

Revision ID: a1b2c3d4e5f6
Revises: 0040d6d4e2cd
Create Date: 2026-05-18 19:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '0040d6d4e2cd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add booking_date column - nullable initially to allow existing rows
    op.add_column('orders', sa.Column('booking_date', sa.Date(), nullable=True))
    
    # Add total_price column - nullable initially to allow existing rows
    op.add_column('orders', sa.Column('total_price', sa.Numeric(precision=10, scale=2), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('orders', 'total_price')
    op.drop_column('orders', 'booking_date')
