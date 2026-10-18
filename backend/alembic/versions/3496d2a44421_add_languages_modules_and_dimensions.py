"""add languages modules and dimensions

Revision ID: 3496d2a44421
Revises: 8bdb4f301e0d
Create Date: 2026-10-13 00:49:35.007238

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3496d2a44421'
down_revision: Union[str, Sequence[str], None] = '8bdb4f301e0d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    languages = op.create_table(
        "languages",
        sa.Column(
            "language_id",
            sa.SmallInteger(),
            sa.Identity(),
            nullable=False,
        ),
        sa.Column("code", sa.String(length=10), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("bengali_name", sa.String(length=50), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("language_id"),
        sa.UniqueConstraint("code"),
        sa.UniqueConstraint("name"),
    )
    modules = op.create_table(
        "modules",
        sa.Column(
            "module_id",
            sa.SmallInteger(),
            sa.Identity(),
            nullable=False,
        ),
        sa.Column("code", sa.String(length=30), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("bengali_name", sa.String(length=50), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("module_id"),
        sa.UniqueConstraint("code"),
        sa.UniqueConstraint("name"),
    )
    dimensions = op.create_table(
        "dimensions",
        sa.Column(
            "dimension_id",
            sa.SmallInteger(),
            sa.Identity(),
            nullable=False,
        ),
        sa.Column("code", sa.String(length=30), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("bengali_name", sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint("dimension_id"),
        sa.UniqueConstraint("code"),
        sa.UniqueConstraint("name"),
    )
    module_dimensions = op.create_table(
        "module_dimensions",
        sa.Column("module_id", sa.SmallInteger(), nullable=False),
        sa.Column("dimension_id", sa.SmallInteger(), nullable=False),
        sa.Column("display_order", sa.SmallInteger(), nullable=False),
        sa.CheckConstraint(
            "display_order > 0",
            name="ck_module_dimensions_positive_display_order",
        ),
        sa.ForeignKeyConstraint(
            ["dimension_id"],
            ["dimensions.dimension_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["module_id"],
            ["modules.module_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("module_id", "dimension_id"),
        sa.UniqueConstraint(
            "module_id",
            "display_order",
            name="uq_module_dimensions_module_display_order",
        ),
    )

    op.bulk_insert(
        languages,
        [
            {
                "language_id": 1,
                "code": "en",
                "name": "English",
                "bengali_name": "ইংরেজি",
                "is_active": True,
            },
            {
                "language_id": 2,
                "code": "de",
                "name": "German",
                "bengali_name": "জার্মান",
                "is_active": True,
            },
            {
                "language_id": 3,
                "code": "es",
                "name": "Spanish",
                "bengali_name": "স্প্যানিশ",
                "is_active": True,
            },
        ],
    )
    op.bulk_insert(
        modules,
        [
            {
                "module_id": 1,
                "code": "speaking",
                "name": "Speaking",
                "bengali_name": "কথা বলা",
                "is_active": True,
            },
            {
                "module_id": 2,
                "code": "reading",
                "name": "Reading",
                "bengali_name": "পড়া",
                "is_active": True,
            },
        ],
    )
    op.bulk_insert(
        dimensions,
        [
            {
                "dimension_id": 1,
                "code": "accuracy",
                "name": "Accuracy",
                "bengali_name": "যথার্থতা",
            },
            {
                "dimension_id": 2,
                "code": "completeness",
                "name": "Completeness",
                "bengali_name": "সম্পূর্ণতা",
            },
            {
                "dimension_id": 3,
                "code": "correctness",
                "name": "Correctness",
                "bengali_name": "শুদ্ধতা",
            },
            {
                "dimension_id": 4,
                "code": "naturalness",
                "name": "Naturalness",
                "bengali_name": "স্বাভাবিকতা",
            },
            {
                "dimension_id": 5,
                "code": "fluency",
                "name": "Fluency",
                "bengali_name": "সাবলীলতা",
            },
        ],
    )
    op.bulk_insert(
        module_dimensions,
        [
            {"module_id": 1, "dimension_id": 1, "display_order": 1},
            {"module_id": 1, "dimension_id": 2, "display_order": 2},
            {"module_id": 1, "dimension_id": 3, "display_order": 3},
            {"module_id": 1, "dimension_id": 4, "display_order": 4},
            {"module_id": 1, "dimension_id": 5, "display_order": 5},
        ],
    )
    for table_name, id_column in (
        ("languages", "language_id"),
        ("modules", "module_id"),
        ("dimensions", "dimension_id"),
    ):
        op.execute(
            f"SELECT setval("
            f"pg_get_serial_sequence('{table_name}', '{id_column}'), "
            f"(SELECT MAX({id_column}) FROM {table_name}), true)"
        )

    op.add_column(
        "speaking_exercises",
        sa.Column("language_id", sa.SmallInteger(), nullable=True),
    )
    op.execute("UPDATE speaking_exercises SET language_id = 1")
    op.alter_column(
        "speaking_exercises",
        "language_id",
        existing_type=sa.SmallInteger(),
        nullable=False,
    )
    op.create_foreign_key(
        "speaking_exercises_language_id_fkey",
        "speaking_exercises",
        "languages",
        ["language_id"],
        ["language_id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_speaking_exercises_language_id",
        "speaking_exercises",
        ["language_id"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_speaking_exercises_language_id",
        table_name="speaking_exercises",
    )
    op.drop_constraint(
        "speaking_exercises_language_id_fkey",
        "speaking_exercises",
        type_="foreignkey",
    )
    op.drop_column("speaking_exercises", "language_id")
    op.drop_table("module_dimensions")
    op.drop_table("dimensions")
    op.drop_table("modules")
    op.drop_table("languages")
