from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, literal, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_optional_current_user
from app.db.session import get_database_session
from app.models.exercise import Exercise
from app.models.language import Language
from app.models.user import User
from app.models.user_exercise import UserExercise
from app.schemas.exercise import CEFRLevel, ExerciseListResponse, ExercisePublic


router = APIRouter(
    prefix="/practice/{source_code}/{target_code}/exercises",
    tags=["Exercises"],
)


async def resolve_language_pair(
    session: AsyncSession,
    source_code: str,
    target_code: str,
) -> tuple[Language, Language]:
    if source_code == target_code:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Source and target languages must be different.",
        )
    languages = list(
        await session.scalars(
            select(Language).where(
                Language.code.in_([source_code, target_code]),
                Language.is_active.is_(True),
            )
        )
    )
    by_code = {language.code: language for language in languages}
    if source_code not in by_code or target_code not in by_code:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source or target language not found.",
        )
    return by_code[source_code], by_code[target_code]


def enforce_native_language(user: User | None, source: Language) -> None:
    if user is not None and user.native_language_id != source.language_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Signed-in users must practise from their native language.",
        )


@router.get("", response_model=ExerciseListResponse)
async def list_exercises(
    source_code: str,
    target_code: str,
    session: AsyncSession = Depends(get_database_session),
    current_user: User | None = Depends(get_optional_current_user),
    level: Annotated[CEFRLevel | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ExerciseListResponse:
    source, target = await resolve_language_pair(session, source_code, target_code)
    enforce_native_language(current_user, source)
    filters = [
        Exercise.is_active.is_(True),
        Exercise.source_language_id == source.language_id,
        Exercise.target_language_id == target.language_id,
    ]
    if level is not None:
        filters.append(Exercise.level == level)

    score_col = (
        UserExercise.overall_score if current_user is not None else literal(None)
    ).label("overall_score")
    query = (
        select(Exercise, score_col, func.count().over().label("total_count"))
        .where(*filters)
        .order_by(Exercise.exercise_id)
        .limit(limit)
        .offset(offset)
    )
    if current_user is not None:
        query = query.outerjoin(
            UserExercise,
            (UserExercise.exercise_id == Exercise.exercise_id)
            & (UserExercise.user_id == current_user.user_id),
        )
    rows = (await session.execute(query)).all()
    total = rows[0].total_count if rows else 0
    if not rows and offset > 0:
        total = await session.scalar(
            select(func.count(Exercise.exercise_id)).where(*filters)
        ) or 0

    return ExerciseListResponse(
        items=[
            ExercisePublic(
                exercise_id=exercise.exercise_id,
                level=exercise.level,
                source_text=exercise.source_text,
                time_limit_seconds=exercise.time_limit_seconds,
                completed=overall_score is not None,
                overall_score=(
                    float(overall_score) if overall_score is not None else None
                ),
            )
            for exercise, overall_score, _ in rows
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{exercise_id}", response_model=ExercisePublic)
async def get_exercise(
    source_code: str,
    target_code: str,
    exercise_id: int,
    session: AsyncSession = Depends(get_database_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> ExercisePublic:
    source, target = await resolve_language_pair(session, source_code, target_code)
    enforce_native_language(current_user, source)
    exercise = await session.scalar(
        select(Exercise).where(
            Exercise.exercise_id == exercise_id,
            Exercise.source_language_id == source.language_id,
            Exercise.target_language_id == target.language_id,
            Exercise.is_active.is_(True),
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
            select(UserExercise.overall_score).where(
                UserExercise.user_id == current_user.user_id,
                UserExercise.exercise_id == exercise.exercise_id,
            )
        )
        overall_score = float(stored_score) if stored_score is not None else None

    return ExercisePublic(
        exercise_id=exercise.exercise_id,
        level=exercise.level,
        source_text=exercise.source_text,
        time_limit_seconds=exercise.time_limit_seconds,
        completed=overall_score is not None,
        overall_score=overall_score,
    )
