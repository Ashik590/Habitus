from typing import Literal, Self

from pydantic import BaseModel, Field, model_validator


FeedbackLanguage = Literal["en", "bn"]


class GeminiEvaluation(BaseModel):
    recognized_translation: str
    is_valid_response: bool = Field(
        description=(
            "Whether a genuine, assessable spoken translation attempt in the "
            "exercise's target language was detected."
        )
    )
    accuracy_score: int = Field(ge=0, le=100)
    completeness_score: int = Field(ge=0, le=100)
    grammar_score: int = Field(ge=0, le=100)
    naturalness_score: int = Field(ge=0, le=100)
    fluency_score: int = Field(ge=0, le=100)
    feedback: str = Field(min_length=1)
    recommended_translations: list[str] = Field(min_length=1, max_length=3)

    @model_validator(mode="after")
    def zero_scores_for_invalid_response(self) -> Self:
        """An invalid speaking attempt cannot carry contradictory positive scores."""
        if not self.is_valid_response:
            self.accuracy_score = 0
            self.completeness_score = 0
            self.grammar_score = 0
            self.naturalness_score = 0
            self.fluency_score = 0
        return self


class EvaluationResponse(BaseModel):
    exercise_id: int
    is_valid_response: bool
    recognized_translation: str
    accuracy_score: int
    completeness_score: int
    grammar_score: int
    naturalness_score: int
    fluency_score: int
    overall_score: float
    feedback: str
    recommended_translations: list[str]
    saved: bool
