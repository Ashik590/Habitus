from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Identity,
    Index,
    SmallInteger,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Exercise(Base):
    __tablename__ = "exercises"
    __table_args__ = (
        CheckConstraint(
            "level IN ('A1', 'A2', 'B1', 'B2', 'C1', 'C2')",
            name="ck_exercises_level",
        ),
        CheckConstraint(
            "time_limit_seconds > 0",
            name="ck_exercises_positive_time_limit",
        ),
        CheckConstraint(
            "cardinality(preferred_solutions) > 0",
            name="ck_exercises_has_preferred_solution",
        ),
        CheckConstraint(
            "source_language_id <> target_language_id",
            name="ck_exercises_different_languages",
        ),
        Index(
            "ix_exercises_language_pair_level",
            "source_language_id",
            "target_language_id",
            "level",
        ),
    )

    exercise_id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(),
        primary_key=True,
    )
    source_language_id: Mapped[int] = mapped_column(
        SmallInteger,
        ForeignKey("languages.language_id", ondelete="RESTRICT"),
        index=True,
    )
    target_language_id: Mapped[int] = mapped_column(
        SmallInteger,
        ForeignKey("languages.language_id", ondelete="RESTRICT"),
        index=True,
    )
    level: Mapped[str] = mapped_column(String(2))
    source_text: Mapped[str] = mapped_column(Text)
    preferred_solutions: Mapped[list[str]] = mapped_column(ARRAY(Text))
    time_limit_seconds: Mapped[int]
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=text("true"),
    )

    user_scores: Mapped[list["UserExercise"]] = relationship(  # noqa: F821
        back_populates="exercise",
        cascade="all, delete-orphan",
    )
    source_language: Mapped["Language"] = relationship(  # noqa: F821
        foreign_keys=[source_language_id],
        back_populates="source_exercises",
    )
    target_language: Mapped["Language"] = relationship(  # noqa: F821
        foreign_keys=[target_language_id],
        back_populates="target_exercises",
    )
