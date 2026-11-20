"""add user profile picture

Revision ID: b8f3c1d9e2a4
Revises: a31d8f6c2e90
Create Date: 2026-11-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b8f3c1d9e2a4"
down_revision: Union[str, Sequence[str], None] = "a31d8f6c2e90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Store the public URL for a user's optional profile picture."""
    op.add_column(
        "users",
        sa.Column("profile_picture_url", sa.String(length=500), nullable=True),
    )


def downgrade() -> None:
    """Remove profile-picture references from users."""
    op.drop_column("users", "profile_picture_url")
