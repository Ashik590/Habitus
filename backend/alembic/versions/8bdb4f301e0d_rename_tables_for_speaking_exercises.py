"""rename tables for speaking exercises

Revision ID: 8bdb4f301e0d
Revises: d40fe0ccf720
Create Date: 2026-10-12 23:58:22.985364

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8bdb4f301e0d'
down_revision: Union[str, Sequence[str], None] = 'd40fe0ccf720'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.rename_table("exercises", "speaking_exercises")
    op.rename_table("user_exercises", "user_speaking_exercises")

    op.execute(
        "ALTER SEQUENCE IF EXISTS exercises_exercise_id_seq "
        "RENAME TO speaking_exercises_exercise_id_seq"
    )

    constraint_renames = (
        ("speaking_exercises", "exercises_pkey", "speaking_exercises_pkey"),
        (
            "speaking_exercises",
            "ck_exercises_level",
            "ck_speaking_exercises_level",
        ),
        (
            "speaking_exercises",
            "ck_exercises_positive_time_limit",
            "ck_speaking_exercises_positive_time_limit",
        ),
        (
            "speaking_exercises",
            "ck_exercises_has_preferred_solution",
            "ck_speaking_exercises_has_preferred_solution",
        ),
        (
            "user_speaking_exercises",
            "user_exercises_pkey",
            "user_speaking_exercises_pkey",
        ),
        (
            "user_speaking_exercises",
            "user_exercises_user_id_fkey",
            "user_speaking_exercises_user_id_fkey",
        ),
        (
            "user_speaking_exercises",
            "user_exercises_exercise_id_fkey",
            "user_speaking_exercises_exercise_id_fkey",
        ),
        (
            "user_speaking_exercises",
            "ck_user_exercises_accuracy_score",
            "ck_user_speaking_exercises_accuracy_score",
        ),
        (
            "user_speaking_exercises",
            "ck_user_exercises_completeness_score",
            "ck_user_speaking_exercises_completeness_score",
        ),
        (
            "user_speaking_exercises",
            "ck_user_exercises_correctness_score",
            "ck_user_speaking_exercises_correctness_score",
        ),
        (
            "user_speaking_exercises",
            "ck_user_exercises_naturalness_score",
            "ck_user_speaking_exercises_naturalness_score",
        ),
        (
            "user_speaking_exercises",
            "ck_user_exercises_fluency_score",
            "ck_user_speaking_exercises_fluency_score",
        ),
        (
            "user_speaking_exercises",
            "ck_user_exercises_overall_score",
            "ck_user_speaking_exercises_overall_score",
        ),
    )
    for table_name, old_name, new_name in constraint_renames:
        op.execute(
            f'ALTER TABLE "{table_name}" '
            f'RENAME CONSTRAINT "{old_name}" TO "{new_name}"'
        )

    op.drop_column("speaking_exercises", "module")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        "speaking_exercises",
        sa.Column(
            "module",
            sa.String(length=30),
            server_default=sa.text("'speaking'"),
            nullable=False,
        ),
    )

    constraint_renames = (
        (
            "user_speaking_exercises",
            "ck_user_speaking_exercises_overall_score",
            "ck_user_exercises_overall_score",
        ),
        (
            "user_speaking_exercises",
            "ck_user_speaking_exercises_fluency_score",
            "ck_user_exercises_fluency_score",
        ),
        (
            "user_speaking_exercises",
            "ck_user_speaking_exercises_naturalness_score",
            "ck_user_exercises_naturalness_score",
        ),
        (
            "user_speaking_exercises",
            "ck_user_speaking_exercises_correctness_score",
            "ck_user_exercises_correctness_score",
        ),
        (
            "user_speaking_exercises",
            "ck_user_speaking_exercises_completeness_score",
            "ck_user_exercises_completeness_score",
        ),
        (
            "user_speaking_exercises",
            "ck_user_speaking_exercises_accuracy_score",
            "ck_user_exercises_accuracy_score",
        ),
        (
            "user_speaking_exercises",
            "user_speaking_exercises_exercise_id_fkey",
            "user_exercises_exercise_id_fkey",
        ),
        (
            "user_speaking_exercises",
            "user_speaking_exercises_user_id_fkey",
            "user_exercises_user_id_fkey",
        ),
        (
            "user_speaking_exercises",
            "user_speaking_exercises_pkey",
            "user_exercises_pkey",
        ),
        (
            "speaking_exercises",
            "ck_speaking_exercises_has_preferred_solution",
            "ck_exercises_has_preferred_solution",
        ),
        (
            "speaking_exercises",
            "ck_speaking_exercises_positive_time_limit",
            "ck_exercises_positive_time_limit",
        ),
        (
            "speaking_exercises",
            "ck_speaking_exercises_level",
            "ck_exercises_level",
        ),
        ("speaking_exercises", "speaking_exercises_pkey", "exercises_pkey"),
    )
    for table_name, old_name, new_name in constraint_renames:
        op.execute(
            f'ALTER TABLE "{table_name}" '
            f'RENAME CONSTRAINT "{old_name}" TO "{new_name}"'
        )

    op.execute(
        "ALTER SEQUENCE IF EXISTS speaking_exercises_exercise_id_seq "
        "RENAME TO exercises_exercise_id_seq"
    )
    op.rename_table("user_speaking_exercises", "user_exercises")
    op.rename_table("speaking_exercises", "exercises")
