from typing import Literal

from pydantic import BaseModel, ConfigDict


CEFRLevel = Literal["A1", "A2", "B1", "B2", "C1", "C2"]


class SpeakingExercisePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    exercise_id: int
    level: CEFRLevel
    bengali_text: str
    time_limit_seconds: int
    completed: bool = False
    overall_score: float | None = None


class SpeakingExerciseListResponse(BaseModel):
    items: list[SpeakingExercisePublic]
    total: int
    limit: int
    offset: int
