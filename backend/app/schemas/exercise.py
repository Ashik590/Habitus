from typing import Literal

from pydantic import BaseModel, ConfigDict


CEFRLevel = Literal["A1", "A2", "B1", "B2", "C1", "C2"]


class ExerciseSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    exercise_id: int
    level: CEFRLevel
    time_limit_seconds: int
    is_public: bool
    is_locked: bool
    completed: bool = False
    overall_score: float | None = None


class ExercisePublic(ExerciseSummary):
    source_text: str


class ExerciseListResponse(BaseModel):
    items: list[ExerciseSummary]
    total: int
    limit: int
    offset: int
