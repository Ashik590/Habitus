"""Add brief source-language exercise titles.

Revision ID: e8fa04b63c12
Revises: d7e9f3a52b01

Existing rows receive neutral placeholders. Apply backend/sql/update_exercise_titles.sql
manually afterward to install the approved titles for the supplied catalog.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e8fa04b63c12"
down_revision: Union[str, Sequence[str], None] = "d7e9f3a52b01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("exercises", sa.Column("title", sa.String(60), nullable=True))
    # Never use prompt excerpts here: list titles are visible to guests too.
    op.execute("""
        UPDATE exercises AS exercise
        SET title = CASE language.code
            WHEN 'bn' THEN 'অনুশীলন #'
            WHEN 'de' THEN 'Übung #'
            WHEN 'es' THEN 'Ejercicio #'
            ELSE 'Exercise #'
        END || exercise.exercise_id::text
        FROM languages AS language
        WHERE exercise.source_language_id = language.language_id
    """)
    op.alter_column("exercises", "title", existing_type=sa.String(60), nullable=False)
    op.create_check_constraint(
        "ck_exercises_title_not_blank", "exercises", "title ~ '[^[:space:]]'",
    )
    op.create_unique_constraint(
        "uq_exercises_language_pair_title", "exercises",
        ["source_language_id", "target_language_id", "title"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_exercises_language_pair_title", "exercises", type_="unique")
    op.drop_constraint("ck_exercises_title_not_blank", "exercises", type_="check")
    op.drop_column("exercises", "title")
