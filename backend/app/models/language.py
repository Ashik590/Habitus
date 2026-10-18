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

    speaking_exercises: Mapped[list["SpeakingExercise"]] = relationship(  # noqa: F821
        back_populates="language"
    )
