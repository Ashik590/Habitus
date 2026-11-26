"""Add usernames and saved target languages; reset existing accounts.

Revision ID: c6d8e2f41a90
Revises: b8f3c1d9e2a4

The account reset is intentional and user-authorized. Running this migration
permanently deletes existing users and their saved exercise scores. Exercise
content and languages are preserved. Downgrading cannot restore deleted data.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c6d8e2f41a90"
down_revision: Union[str, Sequence[str], None] = "b8f3c1d9e2a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DELETE FROM user_exercises")
    op.execute("DELETE FROM users")
    op.add_column("users", sa.Column("username", sa.String(30), nullable=False))
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.alter_column("users", "email", existing_type=sa.String(320), nullable=True)
    op.add_column("users", sa.Column("target_language_id", sa.SmallInteger(), nullable=False))
    op.create_foreign_key(
        "users_target_language_id_fkey", "users", "languages",
        ["target_language_id"], ["language_id"], ondelete="RESTRICT",
    )
    op.create_index("ix_users_target_language_id", "users", ["target_language_id"])
    op.create_check_constraint(
        "ck_users_username_format", "users", "username ~ '^[a-z][a-z0-9_]{2,29}$'",
    )
    op.create_check_constraint(
        "ck_users_different_languages", "users", "native_language_id <> target_language_id",
    )


def downgrade() -> None:
    # Restoring mandatory email requires the owner to resolve optional emails first.
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM users WHERE email IS NULL) THEN
                RAISE EXCEPTION 'Provide email addresses for all users before downgrading.';
            END IF;
        END $$;
    """)
    op.drop_constraint("ck_users_different_languages", "users", type_="check")
    op.drop_constraint("ck_users_username_format", "users", type_="check")
    op.drop_index("ix_users_target_language_id", table_name="users")
    op.drop_constraint("users_target_language_id_fkey", "users", type_="foreignkey")
    op.drop_column("users", "target_language_id")
    op.alter_column("users", "email", existing_type=sa.String(320), nullable=False)
    op.drop_index("ix_users_username", table_name="users")
    op.drop_column("users", "username")
