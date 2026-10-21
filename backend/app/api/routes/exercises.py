from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, literal, select
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

    score_col = (
        UserSpeakingExercise.overall_score
        if current_user is not None
        else literal(None)
    ).label("overall_score")

    query = (
        select(
            SpeakingExercise,
            score_col,
            func.count().over().label("total_count"),
        )
        .join(Language)
        .where(*filters)
        .order_by(SpeakingExercise.exercise_id)
        .limit(limit)
        .offset(offset)
    )

    if current_user is not None:
        query = query.outerjoin(
            UserSpeakingExercise,
            (UserSpeakingExercise.exercise_id == SpeakingExercise.exercise_id)
            & (UserSpeakingExercise.user_id == current_user.user_id),
        )

    rows = (await session.execute(query)).all()

    if not rows and offset > 0:
        total = (
            await session.scalar(
                select(func.count(SpeakingExercise.exercise_id))
                .join(Language)
                .where(*filters)
            )
            or 0
        )
    else:
        total = rows[0].total_count if rows else 0

    items = [
        SpeakingExercisePublic(
            exercise_id=exercise.exercise_id,
            level=exercise.level,
            bengali_text=exercise.bengali_text,
            time_limit_seconds=exercise.time_limit_seconds,
            completed=overall_score is not None,
            overall_score=float(overall_score) if overall_score is not None else None,
        )
        for exercise, overall_score, _ in rows
    ]

    return SpeakingExerciseListResponse(
        items=items,
        total=total,
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
