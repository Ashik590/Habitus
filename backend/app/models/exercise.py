from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Identity,
    SmallInteger,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class SpeakingExercise(Base):
    __tablename__ = "speaking_exercises"
    __table_args__ = (
        CheckConstraint(
            "level IN ('A1', 'A2', 'B1', 'B2', 'C1')",
            name="ck_speaking_exercises_level",
        ),
        CheckConstraint(
            "time_limit_seconds > 0",
            name="ck_speaking_exercises_positive_time_limit",
        ),
        CheckConstraint(
            "cardinality(preferred_solutions) > 0",
            name="ck_speaking_exercises_has_preferred_solution",
        ),
    )

    exercise_id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(),
        primary_key=True,
    )
    language_id: Mapped[int] = mapped_column(
        SmallInteger,
        ForeignKey("languages.language_id", ondelete="RESTRICT"),
        index=True,
    )
    level: Mapped[str] = mapped_column(String(2))
    bengali_text: Mapped[str] = mapped_column(Text)
    preferred_solutions: Mapped[list[str]] = mapped_column(ARRAY(Text))
    time_limit_seconds: Mapped[int]
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=text("true"),
    )

    user_scores: Mapped[list["UserSpeakingExercise"]] = relationship(  # noqa: F821
        back_populates="speaking_exercise",
        cascade="all, delete-orphan",
    )
    language: Mapped["Language"] = relationship(  # noqa: F821
        back_populates="speaking_exercises"
    )
