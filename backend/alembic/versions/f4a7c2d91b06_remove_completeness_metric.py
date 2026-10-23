"""remove completeness metric

Revision ID: f4a7c2d91b06
Revises: e789f1a2b3c4
Create Date: 2026-10-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f4a7c2d91b06"
down_revision: Union[str, Sequence[str], None] = "e789f1a2b3c4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove completeness from stored speaking scores and module metadata."""
    op.drop_constraint(
        "ck_user_speaking_exercises_completeness_score",
        "user_speaking_exercises",
        type_="check",
    )
    op.drop_column("user_speaking_exercises", "completeness_score")

    op.execute(
        """
        DELETE FROM module_dimensions AS md
        USING dimensions AS d
        WHERE md.dimension_id = d.dimension_id
          AND d.code = 'completeness'
        """
    )
    op.execute("DELETE FROM dimensions WHERE code = 'completeness'")
    op.execute(
        """
        UPDATE module_dimensions AS md
        SET display_order = md.display_order + 10
        FROM modules AS m
        WHERE md.module_id = m.module_id
          AND m.code = 'speaking'
          AND md.display_order > 2
        """
    )
    op.execute(
        """
        UPDATE module_dimensions AS md
        SET display_order = md.display_order - 11
        FROM modules AS m
        WHERE md.module_id = m.module_id
          AND m.code = 'speaking'
          AND md.display_order >= 13
        """
    )


def downgrade() -> None:
    """Restore completeness metadata and a zero-valued score column."""
    op.add_column(
        "user_speaking_exercises",
        sa.Column(
            "completeness_score",
            sa.Numeric(precision=5, scale=2),
            server_default=sa.text("0"),
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_user_speaking_exercises_completeness_score",
        "user_speaking_exercises",
        "completeness_score BETWEEN 0 AND 100",
    )
    op.alter_column(
        "user_speaking_exercises",
        "completeness_score",
        server_default=None,
    )

    # Move existing Speaking dimensions out of the way before restoring
    # Completeness to display position 2.
    op.execute(
        """
        UPDATE module_dimensions AS md
        SET display_order = md.display_order + 10
        FROM modules AS m
        WHERE md.module_id = m.module_id
          AND m.code = 'speaking'
          AND md.display_order >= 2
        """
    )
    op.execute(
        """
        UPDATE module_dimensions AS md
        SET display_order = md.display_order - 9
        FROM modules AS m
        WHERE md.module_id = m.module_id
          AND m.code = 'speaking'
          AND md.display_order >= 12
        """
    )
    op.execute(
        """
        INSERT INTO dimensions (code, name, bengali_name)
        VALUES ('completeness', 'Completeness', 'সম্পূর্ণতা')
        ON CONFLICT (code) DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO module_dimensions (module_id, dimension_id, display_order)
        SELECT m.module_id, d.dimension_id, 2
        FROM modules AS m
        CROSS JOIN dimensions AS d
        WHERE m.code = 'speaking'
          AND d.code = 'completeness'
        ON CONFLICT (module_id, dimension_id) DO NOTHING
        """
    )
