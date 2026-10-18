from typing import Literal

from pydantic import BaseModel, Field


FeedbackLanguage = Literal["en", "bn"]


class GeminiEvaluation(BaseModel):
    recognized_translation: str
    is_valid_response: bool = Field(
        description="Whether understandable spoken English translation was detected."
    )
    accuracy_score: int = Field(ge=0, le=100)
    completeness_score: int = Field(ge=0, le=100)
    grammar_score: int = Field(ge=0, le=100)
    naturalness_score: int = Field(ge=0, le=100)
    fluency_score: int = Field(ge=0, le=100)
    overall_score: float = Field(ge=0, le=100)
    feedback: str = Field(min_length=1)
    recommended_translations: list[str] = Field(min_length=1, max_length=3)


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
