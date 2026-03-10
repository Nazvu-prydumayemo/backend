"""seed default user roles

Revision ID: 2b0d1f5e9c11
Revises: 1afa124322f5
Create Date: 2026-03-10 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2b0d1f5e9c11"
down_revision: Union[str, Sequence[str], None] = "1afa124322f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Seed default user roles required by role-based auth."""
    op.execute(
        sa.text(
            """
            INSERT INTO user_roles (id, name)
            SELECT 1, 'admin'
            WHERE NOT EXISTS (SELECT 1 FROM user_roles WHERE id = 1 OR name = 'admin');
            """
        )
    )
    op.execute(
        sa.text(
            """
            INSERT INTO user_roles (id, name)
            SELECT 2, 'moderator'
            WHERE NOT EXISTS (SELECT 1 FROM user_roles WHERE id = 2 OR name = 'moderator');
            """
        )
    )
    op.execute(
        sa.text(
            """
            INSERT INTO user_roles (id, name)
            SELECT 3, 'user'
            WHERE NOT EXISTS (SELECT 1 FROM user_roles WHERE id = 3 OR name = 'user');
            """
        )
    )


def downgrade() -> None:
    """Remove seeded default user roles."""
    op.execute(
        sa.text(
            """
            DELETE FROM user_roles
            WHERE id IN (1, 2, 3)
              AND name IN ('admin', 'moderator', 'user');
            """
        )
    )
