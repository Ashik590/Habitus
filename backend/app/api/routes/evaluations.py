from decimal import Decimal, ROUND_HALF_UP
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.api.dependencies.auth import get_optional_current_user
from app.db.session import get_database_session
from app.models.exercise import SpeakingExercise
from app.models.language import Language
from app.models.user import User
from app.models.user_exercise import UserSpeakingExercise
from app.schemas.evaluation import (
    EvaluationResponse,
    FeedbackLanguage,
    GeminiEvaluation,
)
from app.services.gemini_evaluation import EvaluationServiceError, evaluate_audio


router = APIRouter(
    prefix="/languages/{language_code}/speaking/exercises",
    tags=["Speaking Evaluations"],
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
    return Decimal(str(evaluation.overall_score)).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )


async def save_authenticated_result(
    session: AsyncSession,
    user: User,
    exercise: SpeakingExercise,
    evaluation: GeminiEvaluation,
    overall_score: Decimal,
) -> None:
    values = {
        "user_id": user.user_id,
        "exercise_id": exercise.exercise_id,
        "accuracy_score": evaluation.accuracy_score,
        "completeness_score": evaluation.completeness_score,
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

    statement = insert(UserSpeakingExercise).values(**values)
    statement = statement.on_conflict_do_update(
        index_elements=[
            UserSpeakingExercise.user_id,
            UserSpeakingExercise.exercise_id,
        ],
        set_=score_columns,
    )
    await session.execute(statement)

    await session.commit()


@router.post("/{exercise_id}/evaluate", response_model=EvaluationResponse)
async def evaluate_exercise(
    language_code: str,
    exercise_id: int,
    audio: Annotated[UploadFile, File(description="The learner's recorded answer")],
    feedback_language: Annotated[FeedbackLanguage, Form()] = "en",
    session: AsyncSession = Depends(get_database_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> EvaluationResponse:
    exercise = await session.scalar(
        select(SpeakingExercise)
        .join(Language)
        .options(joinedload(SpeakingExercise.language))
        .where(
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
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
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
        completeness_score=evaluation.completeness_score,
        grammar_score=evaluation.grammar_score,
        naturalness_score=evaluation.naturalness_score,
        fluency_score=evaluation.fluency_score,
        overall_score=float(overall_score),
        feedback=evaluation.feedback,
        recommended_translations=evaluation.recommended_translations,
        saved=should_save,
    )
