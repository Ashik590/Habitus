"""Store details and completion time for the latest saved evaluation.

Revision ID: a10c26d85e34
Revises: f90b15c74d23
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "a10c26d85e34"
down_revision: Union[str, Sequence[str], None] = "f90b15c74d23"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Older scores have no known transcript, feedback, or completion time.
    op.add_column("user_exercises", sa.Column("recognized_translation", sa.Text(), nullable=True))
    op.add_column("user_exercises", sa.Column("feedback", postgresql.ARRAY(sa.Text()), nullable=True))
    op.add_column("user_exercises", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("user_exercises", "completed_at")
    op.drop_column("user_exercises", "feedback")
    op.drop_column("user_exercises", "recognized_translation")
