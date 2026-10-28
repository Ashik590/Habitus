from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.api.routes.exercises import resolve_language_pair
from app.db.session import get_database_session
from app.models.exercise import Exercise
from app.models.language import Language
from app.models.user import User
from app.models.user_exercise import UserExercise
from app.schemas.exercise import CEFRLevel
from app.schemas.statistics import DimensionAverages, LevelStatistics, StatisticsResponse
from app.schemas.user import NativeLanguageUpdate, UserResponse


router = APIRouter(prefix="/users", tags=["Users"])
CEFR_LEVELS: tuple[CEFRLevel, ...] = ("A1", "A2", "B1", "B2", "C1", "C2")


@router.get("/me", response_model=UserResponse)
async def get_my_profile(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.patch("/me/native-language", response_model=UserResponse)
async def update_native_language(
    update: NativeLanguageUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_database_session),
) -> User:
    language = await session.scalar(
        select(Language).where(
            Language.code == update.native_language_code,
            Language.is_active.is_(True),
        )
    )
    if language is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The selected native language is unavailable.",
        )
    current_user.native_language_id = language.language_id
    current_user.native_language = language
    await session.commit()
    return current_user


def optional_average(value: object) -> float | None:
    return round(float(value), 2) if value is not None else None


@router.get(
    "/me/practice/{source_code}/{target_code}/statistics",
    response_model=StatisticsResponse,
)
async def get_my_statistics(
    source_code: str,
    target_code: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_database_session),
) -> StatisticsResponse:
    source, target = await resolve_language_pair(session, source_code, target_code)
    if current_user.native_language_id != source.language_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Statistics must use your current native language as the source.",
        )
    pair_filters = [
        Exercise.source_language_id == source.language_id,
        Exercise.target_language_id == target.language_id,
    ]
    available_rows = await session.execute(
        select(Exercise.level, func.count(Exercise.exercise_id))
        .where(Exercise.is_active.is_(True), *pair_filters)
        .group_by(Exercise.level)
    )
    available_by_level = {
        level: int(count) for level, count in available_rows.all()
    }

    score_rows = await session.execute(
        select(
            Exercise.level,
            func.count(UserExercise.exercise_id),
            func.avg(UserExercise.overall_score),
        )
        .join(Exercise, Exercise.exercise_id == UserExercise.exercise_id)
        .where(UserExercise.user_id == current_user.user_id, *pair_filters)
        .group_by(Exercise.level)
    )
    scores_by_level = {row[0]: row for row in score_rows.all()}
    dimension_row = (
        await session.execute(
            select(
                func.avg(UserExercise.accuracy_score),
                func.avg(UserExercise.grammar_score),
                func.avg(UserExercise.naturalness_score),
                func.avg(UserExercise.fluency_score),
            )
            .join(Exercise, Exercise.exercise_id == UserExercise.exercise_id)
            .where(UserExercise.user_id == current_user.user_id, *pair_filters)
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

    return StatisticsResponse(
        source_language=source.code,
        target_language=target.code,
        exercises_completed=total_completed,
        level_scores=levels,
        dimension_averages=DimensionAverages(
            accuracy=optional_average(dimension_row[0]),
            grammar=optional_average(dimension_row[1]),
            naturalness=optional_average(dimension_row[2]),
            fluency=optional_average(dimension_row[3]),
        ),
    )
