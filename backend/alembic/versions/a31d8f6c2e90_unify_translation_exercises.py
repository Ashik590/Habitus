"""unify translation exercises

Revision ID: a31d8f6c2e90
Revises: f4a7c2d91b06
Create Date: 2026-10-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a31d8f6c2e90"
down_revision: Union[str, Sequence[str], None] = "f4a7c2d91b06"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Move from modules to source-to-target translation exercises."""
    op.execute(
        """
        INSERT INTO languages (code, name, bengali_name, is_active)
        VALUES ('bn', 'Bengali', 'বাংলা', true)
        ON CONFLICT (code) DO NOTHING
        """
    )

    op.add_column(
        "users",
        sa.Column("native_language_id", sa.SmallInteger(), nullable=True),
    )
    op.execute(
        """
        UPDATE users
        SET native_language_id = (
            SELECT language_id FROM languages WHERE code = 'bn'
        )
        """
    )
    op.alter_column("users", "native_language_id", nullable=False)
    op.create_foreign_key(
        "users_native_language_id_fkey",
        "users",
        "languages",
        ["native_language_id"],
        ["language_id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_users_native_language_id",
        "users",
        ["native_language_id"],
    )

    op.rename_table("speaking_exercises", "exercises")
    op.execute(
        "ALTER SEQUENCE IF EXISTS speaking_exercises_exercise_id_seq "
        "RENAME TO exercises_exercise_id_seq"
    )
    for old_name, new_name in (
        ("speaking_exercises_pkey", "exercises_pkey"),
        ("ck_speaking_exercises_level", "ck_exercises_level"),
        (
            "ck_speaking_exercises_positive_time_limit",
            "ck_exercises_positive_time_limit",
        ),
        (
            "ck_speaking_exercises_has_preferred_solution",
            "ck_exercises_has_preferred_solution",
        ),
        (
            "speaking_exercises_language_id_fkey",
            "exercises_target_language_id_fkey",
        ),
    ):
        op.execute(
            f'ALTER TABLE exercises RENAME CONSTRAINT "{old_name}" TO "{new_name}"'
        )

    op.drop_index("ix_speaking_exercises_language_id", table_name="exercises")
    op.alter_column("exercises", "language_id", new_column_name="target_language_id")
    op.alter_column("exercises", "bengali_text", new_column_name="source_text")
    op.add_column(
        "exercises",
        sa.Column("source_language_id", sa.SmallInteger(), nullable=True),
    )
    op.execute(
        """
        UPDATE exercises
        SET source_language_id = (
            SELECT language_id FROM languages WHERE code = 'bn'
        )
        """
    )
    op.alter_column("exercises", "source_language_id", nullable=False)
    op.create_foreign_key(
        "exercises_source_language_id_fkey",
        "exercises",
        "languages",
        ["source_language_id"],
        ["language_id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        "ck_exercises_different_languages",
        "exercises",
        "source_language_id <> target_language_id",
    )
    op.create_index(
        "ix_exercises_source_language_id",
        "exercises",
        ["source_language_id"],
    )
    op.create_index(
        "ix_exercises_target_language_id",
        "exercises",
        ["target_language_id"],
    )
    op.create_index(
        "ix_exercises_language_pair_level",
        "exercises",
        ["source_language_id", "target_language_id", "level"],
    )

    op.rename_table("user_speaking_exercises", "user_exercises")
    for old_name, new_name in (
        ("user_speaking_exercises_pkey", "user_exercises_pkey"),
        (
            "user_speaking_exercises_user_id_fkey",
            "user_exercises_user_id_fkey",
        ),
        (
            "user_speaking_exercises_exercise_id_fkey",
            "user_exercises_exercise_id_fkey",
        ),
        (
            "ck_user_speaking_exercises_accuracy_score",
            "ck_user_exercises_accuracy_score",
        ),
        (
            "ck_user_speaking_exercises_grammar_score",
            "ck_user_exercises_grammar_score",
        ),
        (
            "ck_user_speaking_exercises_naturalness_score",
            "ck_user_exercises_naturalness_score",
        ),
        (
            "ck_user_speaking_exercises_fluency_score",
            "ck_user_exercises_fluency_score",
        ),
        (
            "ck_user_speaking_exercises_overall_score",
            "ck_user_exercises_overall_score",
        ),
    ):
        op.execute(
            f'ALTER TABLE user_exercises RENAME CONSTRAINT "{old_name}" TO "{new_name}"'
        )

    op.drop_table("module_dimensions")
    op.drop_table("dimensions")
    op.drop_table("modules")


def downgrade() -> None:
    """Restore the previous speaking-module schema."""
    op.create_table(
        "modules",
        sa.Column("module_id", sa.SmallInteger(), sa.Identity(), primary_key=True),
        sa.Column("code", sa.String(30), nullable=False, unique=True),
        sa.Column("name", sa.String(50), nullable=False, unique=True),
        sa.Column("bengali_name", sa.String(50), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
    )
    op.create_table(
        "dimensions",
        sa.Column("dimension_id", sa.SmallInteger(), sa.Identity(), primary_key=True),
        sa.Column("code", sa.String(30), nullable=False, unique=True),
        sa.Column("name", sa.String(50), nullable=False, unique=True),
        sa.Column("bengali_name", sa.String(50), nullable=False),
    )
    op.create_table(
        "module_dimensions",
        sa.Column("module_id", sa.SmallInteger(), sa.ForeignKey("modules.module_id", ondelete="CASCADE"), primary_key=True),
        sa.Column("dimension_id", sa.SmallInteger(), sa.ForeignKey("dimensions.dimension_id", ondelete="CASCADE"), primary_key=True),
        sa.Column("display_order", sa.SmallInteger(), nullable=False),
        sa.CheckConstraint("display_order > 0", name="ck_module_dimensions_positive_display_order"),
        sa.UniqueConstraint("module_id", "display_order", name="uq_module_dimensions_module_display_order"),
    )
    op.execute(
        """
        INSERT INTO modules (code, name, bengali_name, is_active)
        VALUES ('speaking', 'Speaking', 'কথা বলা', true),
               ('reading', 'Reading', 'পড়া', true)
        """
    )
    op.execute(
        """
        INSERT INTO dimensions (code, name, bengali_name)
        VALUES ('accuracy', 'Accuracy', 'যথার্থতা'),
               ('grammar', 'Grammar', 'ব্যাকরণ'),
               ('naturalness', 'Naturalness', 'স্বাভাবিকতা'),
               ('fluency', 'Fluency', 'সাবলীলতা')
        """
    )
    op.execute(
        """
        INSERT INTO module_dimensions (module_id, dimension_id, display_order)
        SELECT m.module_id, d.dimension_id,
               CASE d.code
                   WHEN 'accuracy' THEN 1 WHEN 'grammar' THEN 2
                   WHEN 'naturalness' THEN 3 ELSE 4
               END
        FROM modules m CROSS JOIN dimensions d
        WHERE m.code = 'speaking'
        """
    )

    for old_name, new_name in (
        ("user_exercises_pkey", "user_speaking_exercises_pkey"),
        ("user_exercises_user_id_fkey", "user_speaking_exercises_user_id_fkey"),
        ("user_exercises_exercise_id_fkey", "user_speaking_exercises_exercise_id_fkey"),
        ("ck_user_exercises_accuracy_score", "ck_user_speaking_exercises_accuracy_score"),
        ("ck_user_exercises_grammar_score", "ck_user_speaking_exercises_grammar_score"),
        ("ck_user_exercises_naturalness_score", "ck_user_speaking_exercises_naturalness_score"),
        ("ck_user_exercises_fluency_score", "ck_user_speaking_exercises_fluency_score"),
        ("ck_user_exercises_overall_score", "ck_user_speaking_exercises_overall_score"),
    ):
        op.execute(f'ALTER TABLE user_exercises RENAME CONSTRAINT "{old_name}" TO "{new_name}"')
    op.rename_table("user_exercises", "user_speaking_exercises")

    op.drop_index("ix_exercises_language_pair_level", table_name="exercises")
    op.drop_index("ix_exercises_target_language_id", table_name="exercises")
    op.drop_index("ix_exercises_source_language_id", table_name="exercises")
    op.drop_constraint("ck_exercises_different_languages", "exercises", type_="check")
    op.drop_constraint("exercises_source_language_id_fkey", "exercises", type_="foreignkey")
    op.drop_column("exercises", "source_language_id")
    op.alter_column("exercises", "source_text", new_column_name="bengali_text")
    op.alter_column("exercises", "target_language_id", new_column_name="language_id")
    op.create_index("ix_speaking_exercises_language_id", "exercises", ["language_id"])
    for old_name, new_name in (
        ("exercises_pkey", "speaking_exercises_pkey"),
        ("ck_exercises_level", "ck_speaking_exercises_level"),
        ("ck_exercises_positive_time_limit", "ck_speaking_exercises_positive_time_limit"),
        ("ck_exercises_has_preferred_solution", "ck_speaking_exercises_has_preferred_solution"),
        ("exercises_target_language_id_fkey", "speaking_exercises_language_id_fkey"),
    ):
        op.execute(f'ALTER TABLE exercises RENAME CONSTRAINT "{old_name}" TO "{new_name}"')
    op.execute(
        "ALTER SEQUENCE IF EXISTS exercises_exercise_id_seq "
        "RENAME TO speaking_exercises_exercise_id_seq"
    )
    op.rename_table("exercises", "speaking_exercises")

    op.drop_index("ix_users_native_language_id", table_name="users")
    op.drop_constraint("users_native_language_id_fkey", "users", type_="foreignkey")
    op.drop_column("users", "native_language_id")
    op.execute(
        """
        DELETE FROM languages
        WHERE code = 'bn'
          AND NOT EXISTS (
              SELECT 1 FROM speaking_exercises WHERE language_id = languages.language_id
          )
        """
    )
