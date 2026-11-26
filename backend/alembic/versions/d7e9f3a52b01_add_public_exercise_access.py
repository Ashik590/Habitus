"""Add public samples and login-required exercise access.

Revision ID: d7e9f3a52b01
Revises: c6d8e2f41a90
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d7e9f3a52b01"
down_revision: Union[str, Sequence[str], None] = "c6d8e2f41a90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "exercises",
        sa.Column("is_public", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    # Choose two existing active samples per level and language pair, even when
    # IDs contain gaps. New inserts remain locked unless explicitly made public.
    op.execute("""
        WITH ranked AS (
            SELECT exercise_id,
                   row_number() OVER (
                       PARTITION BY source_language_id, target_language_id, level
                       ORDER BY exercise_id
                   ) AS sample_number
            FROM exercises
            WHERE is_active = true
        )
        UPDATE exercises AS exercise
        SET is_public = true
        FROM ranked
        WHERE exercise.exercise_id = ranked.exercise_id
          AND ranked.sample_number <= 2
    """)


def downgrade() -> None:
    op.drop_column("exercises", "is_public")
