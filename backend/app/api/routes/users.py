from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.db.session import get_database_session
from app.models.exercise import SpeakingExercise
from app.models.language import Language
from app.models.user import User
from app.models.user_exercise import UserSpeakingExercise
from app.schemas.exercise import CEFRLevel
from app.schemas.statistics import (
    DimensionAverages,
    LevelStatistics,
    SpeakingStatisticsResponse,
)
from app.schemas.user import UserResponse


router = APIRouter(prefix="/users", tags=["Users"])
CEFR_LEVELS: tuple[CEFRLevel, ...] = ("A1", "A2", "B1", "B2", "C1", "C2")


@router.get("/me", response_model=UserResponse)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
) -> User:
    return current_user


def optional_average(value: object) -> float | None:
    return round(float(value), 2) if value is not None else None


@router.get(
    "/me/languages/{language_code}/speaking/statistics",
    response_model=SpeakingStatisticsResponse,
)
async def get_my_statistics(
    language_code: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_database_session),
) -> SpeakingStatisticsResponse:
    language = await session.scalar(
        select(Language).where(
            Language.code == language_code,
            Language.is_active.is_(True),
        )
    )
    if language is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Language not found.",
        )

    available_rows = await session.execute(
        select(SpeakingExercise.level, func.count(SpeakingExercise.exercise_id))
        .where(
            SpeakingExercise.language_id == language.language_id,
            SpeakingExercise.is_active.is_(True),
        )
        .group_by(SpeakingExercise.level)
    )
    available_by_level = {
        level: int(count) for level, count in available_rows.all()
    }

    score_rows = await session.execute(
        select(
            SpeakingExercise.level,
            func.count(UserSpeakingExercise.exercise_id),
            func.avg(UserSpeakingExercise.overall_score),
        )
        .join(
            SpeakingExercise,
            SpeakingExercise.exercise_id == UserSpeakingExercise.exercise_id,
        )
        .where(
            UserSpeakingExercise.user_id == current_user.user_id,
            SpeakingExercise.language_id == language.language_id,
        )
        .group_by(SpeakingExercise.level)
    )
    scores_by_level = {row[0]: row for row in score_rows.all()}

    dimension_row = (
        await session.execute(
            select(
                func.avg(UserSpeakingExercise.accuracy_score),
                func.avg(UserSpeakingExercise.grammar_score),
                func.avg(UserSpeakingExercise.naturalness_score),
                func.avg(UserSpeakingExercise.fluency_score),
            )
            .join(
                SpeakingExercise,
                SpeakingExercise.exercise_id
                == UserSpeakingExercise.exercise_id,
            )
            .where(
                UserSpeakingExercise.user_id == current_user.user_id,
                SpeakingExercise.language_id == language.language_id,
            )
        )
    ).one()

    levels: list[LevelStatistics] = []
    total_completed = 0

    for level in CEFR_LEVELS:
        score_row = scores_by_level.get(level)
        completed = int(score_row[1]) if score_row is not None else 0
        total_completed += completed

        levels.append(
            LevelStatistics(
                level=level,
                current_score=(
                    optional_average(score_row[2])
                    if score_row is not None
                    else None
                ),
                exercises_completed=completed,
                exercises_available=available_by_level.get(level, 0),
            )
        )

    return SpeakingStatisticsResponse(
        language=language.code,
        exercises_completed=total_completed,
        level_scores=levels,
        dimension_averages=DimensionAverages(
            accuracy=optional_average(dimension_row[0]),
            grammar=optional_average(dimension_row[1]),
            naturalness=optional_average(dimension_row[2]),
            fluency=optional_average(dimension_row[3]),
        ),
    )
