from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, SmallInteger, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "username ~ '^[a-z][a-z0-9_]{2,29}$'",
            name="ck_users_username_format",
        ),
        CheckConstraint(
            "native_language_id <> target_language_id",
            name="ck_users_different_languages",
        ),
    )

    user_id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(100))
    username: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(320), unique=True, index=True)
    native_language_id: Mapped[int] = mapped_column(
        SmallInteger,
        ForeignKey("languages.language_id", ondelete="RESTRICT"),
        index=True,
    )
    target_language_id: Mapped[int] = mapped_column(
        SmallInteger,
        ForeignKey("languages.language_id", ondelete="RESTRICT"),
        index=True,
    )
    password_hash: Mapped[str] = mapped_column(String(255))
    profile_picture_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=text("true"),
    )
    native_language: Mapped["Language"] = relationship(  # noqa: F821
        foreign_keys=[native_language_id],
        back_populates="native_users",
    )
    target_language: Mapped["Language"] = relationship(  # noqa: F821
        foreign_keys=[target_language_id],
        back_populates="target_users",
    )
    exercise_scores: Mapped[list["UserExercise"]] = relationship(  # noqa: F821
        back_populates="user",
        cascade="all, delete-orphan",
    )
