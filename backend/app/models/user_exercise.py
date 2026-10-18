from decimal import Decimal
from uuid import UUID

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class UserSpeakingExercise(Base):
    __tablename__ = "user_speaking_exercises"
    __table_args__ = (
        CheckConstraint(
            "accuracy_score BETWEEN 0 AND 100",
            name="ck_user_speaking_exercises_accuracy_score",
        ),
        CheckConstraint(
            "completeness_score BETWEEN 0 AND 100",
            name="ck_user_speaking_exercises_completeness_score",
        ),
        CheckConstraint(
            "grammar_score BETWEEN 0 AND 100",
            name="ck_user_speaking_exercises_grammar_score",
        ),
        CheckConstraint(
            "naturalness_score BETWEEN 0 AND 100",
            name="ck_user_speaking_exercises_naturalness_score",
        ),
        CheckConstraint(
            "fluency_score BETWEEN 0 AND 100",
            name="ck_user_speaking_exercises_fluency_score",
        ),
        CheckConstraint(
            "overall_score BETWEEN 0 AND 100",
            name="ck_user_speaking_exercises_overall_score",
        ),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"),
        primary_key=True,
    )
    exercise_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("speaking_exercises.exercise_id", ondelete="CASCADE"),
        primary_key=True,
    )

    accuracy_score: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    completeness_score: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    grammar_score: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    naturalness_score: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    fluency_score: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    overall_score: Mapped[Decimal] = mapped_column(Numeric(5, 2))

    user: Mapped["User"] = relationship(  # noqa: F821
        back_populates="speaking_exercise_scores"
    )
    speaking_exercise: Mapped["SpeakingExercise"] = relationship(  # noqa: F821
        back_populates="user_scores"
    )
