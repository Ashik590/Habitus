import asyncio
from functools import lru_cache
import io
import logging
import wave

from faster_whisper import WhisperModel
from google import genai
from google.genai import errors, types
import numpy as np
from pydantic import ValidationError

from app.core.config import settings
from app.models.exercise import SpeakingExercise
from app.schemas.evaluation import FeedbackLanguage, GeminiEvaluation


logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_whisper_model() -> WhisperModel:
    """Load Whisper model once into RAM for instant local CPU transcription."""
    logger.info("Loading local Whisper model '%s' on CPU...", settings.whisper_model)
    return WhisperModel(
        settings.whisper_model,
        device="cpu",
        compute_type="int8",
    )


def _wav_bytes_to_numpy(wav_bytes: bytes) -> np.ndarray:
    """Convert 16 kHz mono 16-bit PCM WAV bytes directly into a float32 NumPy array."""
    with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
        frames = wf.readframes(wf.getnframes())
        return np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0


def transcribe_audio_locally(wav_bytes: bytes, language_code: str) -> str:
    """Transcribe audio locally using faster-whisper with Silero VAD filtering."""
    try:
        model = get_whisper_model()
        audio_array = _wav_bytes_to_numpy(wav_bytes)
        segments, _ = model.transcribe(
            audio_array,
            language=language_code,
            beam_size=5,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500),
        )
        text = " ".join(segment.text.strip() for segment in segments).strip()
        return text
    except Exception as exc:
        logger.exception("Local Whisper transcription failed")
        raise EvaluationServiceError("Local speech transcription failed.") from exc


class EvaluationServiceError(Exception):
    """Raised when Gemini cannot produce a usable evaluation."""


def _extract_json_response(response_text: str) -> str:
    """Remove an optional Markdown fence before Pydantic validates the JSON."""
    text = response_text.strip()
    if text.startswith("```json"):
        text = text.removeprefix("```json").strip()
    elif text.startswith("```"):
        text = text.removeprefix("```").strip()
    if text.endswith("```"):
        text = text.removesuffix("```").strip()
    return text


def _normalize_audio(
    audio_bytes: bytes,
    mime_type: str,
) -> tuple[bytes, str, str]:
    """Normalize every accepted recording to 16 kHz mono PCM WAV."""
    try:
        import av
    except ImportError as exc:
        raise EvaluationServiceError(
            "Audio processing requires the 'av' Python package."
        ) from exc

    source = io.BytesIO(audio_bytes)
    destination = io.BytesIO()

    try:
        with av.open(source, mode="r") as input_container:
            input_stream = input_container.streams.audio[0]
            with av.open(destination, mode="w", format="wav") as output_container:
                output_stream = output_container.add_stream("pcm_s16le", rate=16000)
                output_stream.layout = "mono"
                resampler = av.AudioResampler(
                    format="s16",
                    layout="mono",
                    rate=16000,
                )

                decoded_frame_count = 0
                for input_packet in input_container.demux(input_stream):
                    try:
                        frames = input_packet.decode()
                    except av.error.InvalidDataError:
                        logger.warning("Skipping an invalid audio packet")
                        continue

                    for frame in frames:
                        decoded_frame_count += 1
                        for normalized_frame in resampler.resample(frame):
                            for output_packet in output_stream.encode(
                                normalized_frame
                            ):
                                output_container.mux(output_packet)

                if decoded_frame_count == 0:
                    raise EvaluationServiceError(
                        "The recording contains no decodable audio."
                    )

                for normalized_frame in resampler.resample(None):
                    for output_packet in output_stream.encode(normalized_frame):
                        output_container.mux(output_packet)
                for output_packet in output_stream.encode(None):
                    output_container.mux(output_packet)
    except Exception as exc:
        logger.exception("Could not normalize uploaded %s audio", mime_type)
        raise EvaluationServiceError(
            "The recording could not be converted for evaluation."
        ) from exc

    return destination.getvalue(), "audio/wav", "wav"


def _generate_with_fallback(
    client: genai.Client,
    contents: list[object] | object,
    temperature: float = 0.0,
):
    model_names = [
        settings.gemini_model,
        *(
            model.strip()
            for model in settings.gemini_fallback_models.split(",")
            if model.strip()
        ),
    ]
    model_names = list(dict.fromkeys(model_names))

    last_error: Exception | None = None
    for model_name in model_names:
        try:
            return client.models.generate_content(
                model=model_name,
                contents=contents,
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    http_options=types.HttpOptions(
                        timeout=30_000,
                        retry_options=types.HttpRetryOptions(attempts=1),
                    ),
                ),
            )
        except (errors.ServerError, errors.ClientError) as exc:
            last_error = exc
            if exc.code not in {404, 429, 500, 502, 503, 504}:
                raise
            logger.warning(
                "Gemini model %s encountered error %s; trying fallback model",
                model_name,
                exc.code,
            )

    if last_error is not None:
        raise last_error
    raise EvaluationServiceError("No Gemini evaluation model is configured.")


def _clean_transcription(text: str) -> str:
    cleaned = text.strip().strip('"').strip("'").strip()
    lowered = cleaned.lower()
    if lowered in {"", "[unintelligible]", "[inaudible]", "[silence]", "[noise]", "none", "null"}:
        return ""
    return cleaned


def build_evaluation_prompt(
    exercise: SpeakingExercise,
    transcribed_text: str,
    feedback_language: FeedbackLanguage,
) -> str:
    """Prompt for the single Gemini evaluation call (audio for acoustic fluency + transcript for linguistic scoring)."""
    feedback_language_name = "Bengali" if feedback_language == "bn" else "English"
    references = "\n".join(
        f"- {solution}" for solution in exercise.preferred_solutions
    )
    target_language = exercise.language.name

    return f"""
You are a strict language examiner evaluating a learner's spoken {target_language} translation.

Source Bengali sentence: {exercise.bengali_text}
CEFR level: {exercise.level}

Reference translations (guidance, other valid translations are also acceptable):
{references}

The learner's speech was independently transcribed by speech recognition as:
"{transcribed_text}"

EVALUATION INSTRUCTIONS:
1. Acoustic Fluency Evaluation (Listen to the attached audio):
   - Listen to the audio ONLY to evaluate vocal delivery, cadence, pauses, rhythm, and speech flow from 0 to 100.
     * 80-100: Smooth, natural pacing with few or no unnatural hesitations.
     * 60-79: Moderate flow, occasional pauses or self-corrections.
     * 40-59: Noticeable hesitations, broken rhythm, or halting delivery.
     * 1-39: Extremely fragmented delivery with long struggling pauses between words.
   - Record this score as fluency_score.

2. Linguistic & Semantic Evaluation (Evaluate the transcribed phrase against the source & references):
   - is_valid_response: Set to true if the response is an actual translation attempt of the source sentence in {target_language}. If it is completely off-topic, nonsense words, or unrelated, set to false.
   - If is_valid_response is false, set all scores (accuracy_score, completeness_score, correctness_score, naturalness_score, fluency_score, overall_score) to 0.
   - If is_valid_response is true, evaluate and score from 0 to 100:
     * accuracy_score: How accurately it conveys the meaning of the source Bengali sentence.
     * completeness_score: Whether all key concepts and words were translated.
     * correctness_score: Grammatical and syntactical correctness in {target_language}.
     * naturalness_score: Idiomatic phrasing and natural word choice.
     * overall_score: Weighted composite score (0 to 100) reflecting all 5 dimensions.

3. Feedback & Recommendations:
   - feedback: Provide concise, constructive feedback in {feedback_language_name} explaining what went well and what can be improved.
   - recommended_translations: Provide 1 to 3 best {target_language} translations.

Return one JSON object with exactly these fields:
recognized_translation, is_valid_response,
accuracy_score, completeness_score, correctness_score, naturalness_score,
fluency_score, overall_score, feedback, and recommended_translations.
In recognized_translation, return: "{transcribed_text}".
""".strip()


def _evaluate_audio_sync(
    exercise: SpeakingExercise,
    audio_bytes: bytes,
    mime_type: str,
    feedback_language: FeedbackLanguage,
) -> GeminiEvaluation:
    if not settings.gemini_api_key:
        raise EvaluationServiceError("Gemini API key is not configured.")

    client = genai.Client(api_key=settings.gemini_api_key)
    normalized_bytes, normalized_mime_type, _ = _normalize_audio(
        audio_bytes,
        mime_type,
    )

    target_language_code = exercise.language.code
    target_language_name = exercise.language.name

    # Step 1: Local Whisper transcription on CPU (~300ms)
    logger.info("Step 1: Running local Whisper transcription for '%s'...", target_language_name)
    raw_transcript = transcribe_audio_locally(normalized_bytes, target_language_code)
    cleaned_transcript = _clean_transcription(raw_transcript)
    logger.info("Step 1 Whisper Result: '%s'", cleaned_transcript)

    # Short-circuit: If no intelligible speech was recognized, stop immediately without calling Gemini!
    if not cleaned_transcript:
        logger.info("Short-circuiting: No speech recognized by Whisper. Returning 0 scores with ZERO Gemini calls.")
        feedback = (
            f"কোনো স্পষ্ট {exercise.language.bengali_name} কথা শনাক্ত করা যায়নি। দয়া করে স্পষ্টভাবে বলুন।"
            if feedback_language == "bn"
            else f"No clear {target_language_name} speech was detected. Please speak clearly and try again."
        )
        return GeminiEvaluation(
            recognized_translation="",
            is_valid_response=False,
            accuracy_score=0,
            completeness_score=0,
            correctness_score=0,
            naturalness_score=0,
            fluency_score=0,
            overall_score=0,
            feedback=feedback,
            recommended_translations=exercise.preferred_solutions[:3],
        )

    # Step 2: Exactly ONE Gemini request (audio for fluency + transcript for linguistic scoring)
    logger.info(
        "Step 2: Sending single evaluation request to Gemini with Whisper transcript '%s'...",
        cleaned_transcript,
    )
    audio_part = types.Part.from_bytes(
        data=normalized_bytes,
        mime_type=normalized_mime_type,
    )
    evaluation_prompt = build_evaluation_prompt(
        exercise,
        cleaned_transcript,
        feedback_language,
    )
    evaluation_response = _generate_with_fallback(
        client,
        contents=[audio_part, evaluation_prompt],
        temperature=0.0,
    )
    logger.info("Gemini Raw Evaluation Response: %s", evaluation_response.text)

    try:
        return GeminiEvaluation.model_validate_json(
            _extract_json_response(evaluation_response.text)
        )
    except (ValidationError, TypeError, ValueError) as exc:
        logger.exception("Gemini returned an invalid evaluation response")
        raise EvaluationServiceError(
            "Gemini returned an invalid evaluation response."
        ) from exc


async def evaluate_audio(
    exercise: SpeakingExercise,
    audio_bytes: bytes,
    mime_type: str,
    feedback_language: FeedbackLanguage,
) -> GeminiEvaluation:
    try:
        return await asyncio.to_thread(
            _evaluate_audio_sync,
            exercise,
            audio_bytes,
            mime_type,
            feedback_language,
        )
    except EvaluationServiceError:
        raise
    except Exception as exc:
        logger.exception("Gemini evaluation request failed")
        raise EvaluationServiceError("Gemini evaluation request failed.") from exc
