"""remove score history

Revision ID: d40fe0ccf720
Revises: 6d284bead38e
Create Date: 2026-10-12 23:40:45.615474

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'd40fe0ccf720'
down_revision: Union[str, Sequence[str], None] = '6d284bead38e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        "ALTER TABLE public.users DROP COLUMN IF EXISTS score_history"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        """
        ALTER TABLE public.users
        ADD COLUMN IF NOT EXISTS score_history JSONB
        NOT NULL DEFAULT '{}'::jsonb
        """
    )
