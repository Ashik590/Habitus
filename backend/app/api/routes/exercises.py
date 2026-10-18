from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_optional_current_user
from app.db.session import get_database_session
from app.models.exercise import SpeakingExercise
from app.models.language import Language
from app.models.user import User
from app.models.user_exercise import UserSpeakingExercise
from app.schemas.exercise import (
    CEFRLevel,
    SpeakingExerciseListResponse,
    SpeakingExercisePublic,
)


router = APIRouter(
    prefix="/languages/{language_code}/speaking/exercises",
    tags=["Speaking Exercises"],
)


@router.get("", response_model=SpeakingExerciseListResponse)
async def list_exercises(
    language_code: str,
    session: AsyncSession = Depends(get_database_session),
    current_user: User | None = Depends(get_optional_current_user),
    level: Annotated[CEFRLevel | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> SpeakingExerciseListResponse:
    filters = [
        SpeakingExercise.is_active.is_(True),
        Language.code == language_code,
        Language.is_active.is_(True),
    ]
    if level is not None:
        filters.append(SpeakingExercise.level == level)

    total = await session.scalar(
        select(func.count(SpeakingExercise.exercise_id))
        .join(Language)
        .where(*filters)
    )
    exercise_rows = await session.scalars(
        select(SpeakingExercise)
        .join(Language)
        .where(*filters)
        .order_by(SpeakingExercise.exercise_id)
        .limit(limit)
        .offset(offset)
    )
    exercises = list(exercise_rows)

    scores_by_exercise_id: dict[int, float] = {}
    if current_user is not None and exercises:
        score_rows = await session.execute(
            select(
                UserSpeakingExercise.exercise_id,
                UserSpeakingExercise.overall_score,
            ).where(
                UserSpeakingExercise.user_id == current_user.user_id,
                UserSpeakingExercise.exercise_id.in_(
                    exercise.exercise_id for exercise in exercises
                ),
            )
        )
        scores_by_exercise_id = {
            exercise_id: float(overall_score)
            for exercise_id, overall_score in score_rows.all()
        }

    items = [
        SpeakingExercisePublic(
            exercise_id=exercise.exercise_id,
            level=exercise.level,
            bengali_text=exercise.bengali_text,
            time_limit_seconds=exercise.time_limit_seconds,
            completed=exercise.exercise_id in scores_by_exercise_id,
            overall_score=scores_by_exercise_id.get(exercise.exercise_id),
        )
        for exercise in exercises
    ]

    return SpeakingExerciseListResponse(
        items=items,
        total=total or 0,
        limit=limit,
        offset=offset,
    )


@router.get("/{exercise_id}", response_model=SpeakingExercisePublic)
async def get_exercise(
    language_code: str,
    exercise_id: int,
    session: AsyncSession = Depends(get_database_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> SpeakingExercisePublic:
    exercise = await session.scalar(
        select(SpeakingExercise).join(Language).where(
            SpeakingExercise.exercise_id == exercise_id,
            SpeakingExercise.is_active.is_(True),
            Language.code == language_code,
            Language.is_active.is_(True),
        )
    )
    if exercise is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exercise not found.",
        )

    overall_score = None
    if current_user is not None:
        stored_score = await session.scalar(
            select(UserSpeakingExercise.overall_score).where(
                UserSpeakingExercise.user_id == current_user.user_id,
                UserSpeakingExercise.exercise_id == exercise.exercise_id,
            )
        )
        if stored_score is not None:
            overall_score = float(stored_score)

    return SpeakingExercisePublic(
        exercise_id=exercise.exercise_id,
        level=exercise.level,
        bengali_text=exercise.bengali_text,
        time_limit_seconds=exercise.time_limit_seconds,
        completed=overall_score is not None,
        overall_score=overall_score,
    )
