from typing import Literal

from pydantic import BaseModel

from app.schemas.exercise import CEFRLevel


class LevelStatistics(BaseModel):
    level: CEFRLevel
    current_score: float | None
    exercises_completed: int
    exercises_available: int


class DimensionAverages(BaseModel):
    accuracy: float | None
    completeness: float | None
    correctness: float | None
    naturalness: float | None
    fluency: float | None


class SpeakingStatisticsResponse(BaseModel):
    language: str
    module: Literal["speaking"] = "speaking"
    exercises_completed: int
    level_scores: list[LevelStatistics]
    dimension_averages: DimensionAverages
