from typing import Literal

from pydantic import BaseModel, ConfigDict


CEFRLevel = Literal["A1", "A2", "B1", "B2", "C1", "C2"]


class ExercisePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    exercise_id: int
    level: CEFRLevel
    source_text: str
    time_limit_seconds: int
    completed: bool = False
    overall_score: float | None = None


class ExerciseListResponse(BaseModel):
    items: list[ExercisePublic]
    total: int
    limit: int
    offset: int
