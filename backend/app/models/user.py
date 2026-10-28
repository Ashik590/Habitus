from uuid import UUID, uuid4

from sqlalchemy import Boolean, ForeignKey, SmallInteger, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    native_language_id: Mapped[int] = mapped_column(
        SmallInteger,
        ForeignKey("languages.language_id", ondelete="RESTRICT"),
        index=True,
    )
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=text("true"),
    )
    native_language: Mapped["Language"] = relationship(  # noqa: F821
        back_populates="native_users"
    )
    exercise_scores: Mapped[list["UserExercise"]] = relationship(  # noqa: F821
        back_populates="user",
        cascade="all, delete-orphan",
    )
