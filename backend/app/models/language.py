from sqlalchemy import Boolean, Identity, SmallInteger, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Language(Base):
    __tablename__ = "languages"

    language_id: Mapped[int] = mapped_column(
        SmallInteger,
        Identity(),
        primary_key=True,
    )
    code: Mapped[str] = mapped_column(String(10), unique=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    bengali_name: Mapped[str] = mapped_column(String(50))
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=text("true"),
    )

    source_exercises: Mapped[list["Exercise"]] = relationship(  # noqa: F821
        foreign_keys="Exercise.source_language_id",
        back_populates="source_language",
    )
    target_exercises: Mapped[list["Exercise"]] = relationship(  # noqa: F821
        foreign_keys="Exercise.target_language_id",
        back_populates="target_language",
    )
    native_users: Mapped[list["User"]] = relationship(  # noqa: F821
        back_populates="native_language"
    )
