"""add_c2_to_speaking_exercises_level

Revision ID: e789f1a2b3c4
Revises: 6954d1f748f3
Create Date: 2026-10-22 19:30:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'e789f1a2b3c4'
down_revision: Union[str, Sequence[str], None] = '6954d1f748f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Allow C2 level in speaking_exercises table."""
    op.drop_constraint("ck_speaking_exercises_level", "speaking_exercises", type_="check")
    op.create_check_constraint(
        "ck_speaking_exercises_level",
        "speaking_exercises",
        "level IN ('A1', 'A2', 'B1', 'B2', 'C1', 'C2')",
    )


def downgrade() -> None:
    """Revert C2 level from speaking_exercises table."""
    op.drop_constraint("ck_speaking_exercises_level", "speaking_exercises", type_="check")
    op.create_check_constraint(
        "ck_speaking_exercises_level",
        "speaking_exercises",
        "level IN ('A1', 'A2', 'B1', 'B2', 'C1')",
    )
