"""Keep exercise titles brief.

Revision ID: f90b15c74d23
Revises: e8fa04b63c12
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f90b15c74d23"
down_revision: Union[str, Sequence[str], None] = "e8fa04b63c12"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Also handle installations that already applied the earlier title SQL.
    op.execute("""
        UPDATE exercises AS exercise
        SET title = brief.new_title
        FROM languages AS source,
             (VALUES
                 ('কৃত্রিম বুদ্ধিমত্তা ও বিচারবোধ', 'কৃত্রিম বুদ্ধিমত্তা'),
                 ('অপ্রত্যাশিত পরিস্থিতির প্রস্তুতি', 'আগাম প্রস্তুতি'),
                 ('নতুন নেতৃত্ব, পুরোনো সমস্যা', 'নেতৃত্বের পরিবর্তন')
             ) AS brief(old_title, new_title)
        WHERE exercise.source_language_id = source.language_id
          AND source.code = 'bn'
          AND exercise.title = brief.old_title
    """)
    # Never silently truncate other, manually authored titles.
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM exercises WHERE char_length(title) > 30) THEN
                RAISE EXCEPTION 'Shorten exercise titles longer than 30 characters before applying this migration.';
            END IF;
        END $$;
    """)
    op.alter_column(
        "exercises", "title", existing_type=sa.String(60),
        type_=sa.String(30), existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "exercises", "title", existing_type=sa.String(30),
        type_=sa.String(60), existing_nullable=False,
    )
