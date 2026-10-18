"""rename_correctness_to_grammar

Revision ID: 6954d1f748f3
Revises: 3496d2a44421
Create Date: 2026-10-18 13:26:41.440170

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6954d1f748f3'
down_revision: Union[str, Sequence[str], None] = '3496d2a44421'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Rename column in user_speaking_exercises
    op.alter_column(
        "user_speaking_exercises",
        "correctness_score",
        new_column_name="grammar_score",
    )

    # 2. Drop old check constraint and create new check constraint
    op.drop_constraint(
        "ck_user_speaking_exercises_correctness_score",
        "user_speaking_exercises",
        type_="check",
    )
    op.create_check_constraint(
        "ck_user_speaking_exercises_grammar_score",
        "user_speaking_exercises",
        "grammar_score BETWEEN 0 AND 100",
    )

    # 3. Update the dimensions table record
    op.execute(
        """
        UPDATE dimensions
        SET code = 'grammar', name = 'Grammar', bengali_name = 'ব্যাকরণ'
        WHERE code = 'correctness';
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    # 1. Revert the dimensions table record
    op.execute(
        """
        UPDATE dimensions
        SET code = 'correctness', name = 'Correctness', bengali_name = 'শুদ্ধতা'
        WHERE code = 'grammar';
        """
    )

    # 2. Drop new check constraint and recreate old check constraint
    op.drop_constraint(
        "ck_user_speaking_exercises_grammar_score",
        "user_speaking_exercises",
        type_="check",
    )
    op.create_check_constraint(
        "ck_user_speaking_exercises_correctness_score",
        "user_speaking_exercises",
        "correctness_score BETWEEN 0 AND 100",
    )

    # 3. Rename column back in user_speaking_exercises
    op.alter_column(
        "user_speaking_exercises",
        "grammar_score",
        new_column_name="correctness_score",
    )
