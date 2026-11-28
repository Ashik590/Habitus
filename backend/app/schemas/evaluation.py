from datetime import datetime
from typing import Literal, Self

from pydantic import BaseModel, Field, model_validator

from app.schemas.exercise import CEFRLevel


FeedbackLanguage = Literal["en", "bn"]


class GeminiEvaluation(BaseModel):
    recognized_translation: str = Field(
        description="Actual audible words, never an expected answer; empty if no words are intelligible."
    )
    is_valid_response: bool = Field(
        description=(
            "Whether a genuine, assessable spoken translation attempt in the "
            "exercise's target language was detected."
        )
    )
    accuracy_score: int = Field(ge=0, le=100)
    grammar_score: int = Field(ge=0, le=100)
    naturalness_score: int = Field(ge=0, le=100)
    fluency_score: int = Field(ge=0, le=100)
    feedback: list[str] = Field(max_length=5)
    recommended_translations: list[str] = Field(min_length=1, max_length=3)

    @model_validator(mode="after")
    def zero_scores_for_invalid_response(self) -> Self:
        """Empty or invalid speech cannot carry contradictory positive scores."""
        self.recognized_translation = self.recognized_translation.strip()
        if not self.recognized_translation:
            self.is_valid_response = False
        if not self.is_valid_response:
            self.accuracy_score = 0
            self.grammar_score = 0
            self.naturalness_score = 0
            self.fluency_score = 0
        return self


class EvaluationResponse(BaseModel):
    exercise_id: int
    is_valid_response: bool
    recognized_translation: str
    accuracy_score: int
    grammar_score: int
    naturalness_score: int
    fluency_score: int
    overall_score: float
    feedback: list[str]
    recommended_translations: list[str]
    saved: bool


class SavedEvaluationResponse(BaseModel):
    exercise_id: int
    title: str
    level: CEFRLevel
    source_text: str
    time_limit_seconds: int
    preferred_solutions: list[str]
    recognized_translation: str | None
    feedback: list[str] | None
    completed_at: datetime | None
    accuracy_score: float
    grammar_score: float
    naturalness_score: float
    fluency_score: float
    overall_score: float
