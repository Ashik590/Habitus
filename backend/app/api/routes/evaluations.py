from decimal import Decimal, ROUND_HALF_UP
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.api.dependencies.auth import get_optional_current_user
from app.db.session import get_database_session
from app.api.routes.exercises import enforce_native_language, resolve_language_pair
from app.models.exercise import Exercise
from app.models.user import User
from app.models.user_exercise import UserExercise
from app.schemas.evaluation import (
    EvaluationResponse,
    FeedbackLanguage,
    GeminiEvaluation,
)
from app.services.gemini_evaluation import EvaluationServiceError, evaluate_audio


router = APIRouter(
    prefix="/practice/{source_code}/{target_code}/exercises",
    tags=["Evaluations"],
)

MAX_AUDIO_SIZE_BYTES = 10 * 1024 * 1024
SUPPORTED_AUDIO_TYPES = {
    "audio/aac",
    "audio/flac",
    "audio/m4a",
    "audio/mp3",
    "audio/mp4",
    "audio/mpeg",
    "audio/ogg",
    "audio/wav",
    "audio/webm",
    "audio/x-m4a",
}


def calculate_overall_score(evaluation: GeminiEvaluation) -> Decimal:
    if not evaluation.is_valid_response:
        return Decimal("0.00")
    weighted = (
        Decimal("0.35") * Decimal(evaluation.accuracy_score)
        + Decimal("0.20") * Decimal(evaluation.grammar_score)
        + Decimal("0.30") * Decimal(evaluation.naturalness_score)
        + Decimal("0.15") * Decimal(evaluation.fluency_score)
    )
    return weighted.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


async def save_authenticated_result(
    session: AsyncSession,
    user: User,
    exercise: Exercise,
    evaluation: GeminiEvaluation,
    overall_score: Decimal,
) -> None:
    values = {
        "user_id": user.user_id,
        "exercise_id": exercise.exercise_id,
        "accuracy_score": evaluation.accuracy_score,
        "grammar_score": evaluation.grammar_score,
        "naturalness_score": evaluation.naturalness_score,
        "fluency_score": evaluation.fluency_score,
        "overall_score": overall_score,
    }
    score_columns = {
        key: value
        for key, value in values.items()
        if key not in {"user_id", "exercise_id"}
    }

    statement = insert(UserExercise).values(**values)
    statement = statement.on_conflict_do_update(
        index_elements=[
            UserExercise.user_id,
            UserExercise.exercise_id,
        ],
        set_=score_columns,
    )
    await session.execute(statement)

    await session.commit()


@router.post("/{exercise_id}/evaluate", response_model=EvaluationResponse)
async def evaluate_exercise(
    source_code: str,
    target_code: str,
    exercise_id: int,
    audio: Annotated[UploadFile, File(description="The learner's recorded answer")],
    feedback_language: Annotated[FeedbackLanguage, Form()] = "en",
    session: AsyncSession = Depends(get_database_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> EvaluationResponse:
    source, target = await resolve_language_pair(session, source_code, target_code)
    enforce_native_language(current_user, source)
    exercise = await session.scalar(
        select(Exercise)
        .options(
            joinedload(Exercise.source_language),
            joinedload(Exercise.target_language),
        )
        .where(
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

    mime_type = (audio.content_type or "").split(";", maxsplit=1)[0].lower()
    if mime_type not in SUPPORTED_AUDIO_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported audio format.",
        )

    try:
        audio_bytes = await audio.read(MAX_AUDIO_SIZE_BYTES + 1)
    finally:
        await audio.close()

    if not audio_bytes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The audio recording is empty.",
        )
    if len(audio_bytes) > MAX_AUDIO_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="The audio recording exceeds the 10 MB limit.",
        )

    normalized_mime_type = "audio/m4a" if mime_type == "audio/x-m4a" else mime_type
    try:
        evaluation = await evaluate_audio(
            exercise,
            audio_bytes,
            normalized_mime_type,
            feedback_language,
        )
    except EvaluationServiceError as exc:
        headers = None
        if exc.retry_after_seconds is not None:
            headers = {"Retry-After": str(exc.retry_after_seconds)}
        raise HTTPException(
            status_code=exc.status_code,
            detail=str(exc),
            headers=headers,
        ) from exc

    overall_score = calculate_overall_score(evaluation)
    should_save = current_user is not None and evaluation.is_valid_response
    if should_save:
        await save_authenticated_result(
            session,
            current_user,
            exercise,
            evaluation,
            overall_score,
        )

    return EvaluationResponse(
        exercise_id=exercise.exercise_id,
        is_valid_response=evaluation.is_valid_response,
        recognized_translation=evaluation.recognized_translation,
        accuracy_score=evaluation.accuracy_score,
        grammar_score=evaluation.grammar_score,
        naturalness_score=evaluation.naturalness_score,
        fluency_score=evaluation.fluency_score,
        overall_score=float(overall_score),
        feedback=evaluation.feedback,
        recommended_translations=evaluation.recommended_translations,
        saved=should_save,
    )
