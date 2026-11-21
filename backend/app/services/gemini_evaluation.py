import asyncio
from functools import lru_cache
import io
import logging
import wave

from faster_whisper import WhisperModel
from google import genai
from google.genai import errors, types
import httpx
import numpy as np
from pydantic import ValidationError

from app.core.config import settings
from app.models.exercise import Exercise
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
            condition_on_previous_text=False,
        )
        text = " ".join(segment.text.strip() for segment in segments).strip()
        return text
    except Exception as exc:
        logger.exception("Local Whisper transcription failed")
        raise EvaluationServiceError("Local speech transcription failed.") from exc


class EvaluationServiceError(Exception):
    """Raised when Gemini cannot produce a usable evaluation."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int = 503,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code


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


def _generate_evaluation(
    contents: list[object] | object,
    temperature: float = 0.0,
):
    """Make one provider request using one key, with SDK retries disabled."""
    if not settings.gemini_api_key or not settings.gemini_api_key.strip():
        logger.error("GEMINI_API_KEY is not configured")
        raise EvaluationServiceError("Please retry again.")

    try:
        with genai.Client(
            api_key=settings.gemini_api_key.strip(),
            http_options=types.HttpOptions(
                timeout=30_000,
                # The SDK counts the initial request as the first attempt.
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        ) as client:
            return client.models.generate_content(
                model=settings.gemini_model,
                contents=contents,
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    response_mime_type="application/json",
                    response_schema=GeminiEvaluation,
                ),
            )
    except (errors.APIError, httpx.HTTPError) as exc:
        logger.exception("Gemini evaluation failed; no automatic retry was attempted")
        raise EvaluationServiceError("Please retry again.") from exc


def _clean_transcription(text: str) -> str:
    cleaned = text.strip().strip('"').strip("'").strip()
    lowered = cleaned.lower()
    if lowered in {"", "[unintelligible]", "[inaudible]", "[silence]", "[noise]", "none", "null"}:
        return ""
    return cleaned


def build_evaluation_prompt(
    exercise: Exercise,
    transcribed_text: str,
    feedback_language: FeedbackLanguage,
) -> str:
    """Compact rubric for audio verification and independent speaking scores."""
    feedback_language_name = "Bengali" if feedback_language == "bn" else "English"
    references = "\n".join(
        f"- {solution}" for solution in exercise.preferred_solutions
    )
    source_language = exercise.source_language.name
    target_language = exercise.target_language.name

    return f"""
Evaluate a learner's spoken {target_language} translation from {source_language}.
Be strict and impartial; assess the actual response without inflated scores.
Return only JSON matching the provided schema.

SOURCE: {exercise.source_text}
CEFR LEVEL: {exercise.level}
REFERENCE TRANSLATIONS (guidance, not mandatory wording):
{references}
INITIAL SPEECH-RECOGNITION TRANSCRIPT: "{transcribed_text}"

TRANSCRIPT AND VALIDITY
Listen to the attached audio and verify the initial transcript. In
recognized_translation, preserve the words actually spoken in {target_language},
including grammatical and vocabulary errors. Correct recognition errors only
when supported by audio; do not invent speech or improve the learner's answer.

A genuine translation attempt is valid even with substantial meaning or grammar
errors. Set is_valid_response=false only for unrelated, meaningless speech,
refusal, or a non-attempt; then set all four scores to zero.

SCORING
Assign independent integer scores from 0 to 100. A problem affects multiple
scores only if it independently violates each criterion. Do not transfer
penalties automatically. Different valid wording and structures are acceptable.

ACCURACY: Complete semantic fidelity, including coverage of the source meaning.
Identify the source's meaningful units and their relative importance: participants,
actions/states, objects, relationships, time/aspect/frequency, location, negation,
conditions, and modifiers. Check which are actually conveyed, not merely which
words overlap. Penalize omissions, additions, substitutions, and contradictions
according to importance; changing a central proposition requires a substantial
reduction even when several words match. Preserve temporal meaning, but accept
different grammatical forms that express the same meaning. Judge meaning, not
word counts, grammar quality, or an equal-weight formula for semantic units.
Bands: 100=fully equivalent with no meaningful difference; 90-99=only an extremely
small nuance differs; 70-89=much preserved with a meaningful detail changed;
40-69=a major component wrong/missing; 1-39=central meaning substantially different
with only fragments corresponding; 0=no meaningful correspondence or invalid.

GRAMMAR: Correctness of the learner's actual target-language construction,
including word order, conjugation, tense/aspect forms, agreement, articles,
prepositions, pronouns/case, and clauses. A wrong meaning can be grammatical.
Pauses, fillers, repetitions, and stutters belong to fluency, not grammar.
Bands: 100=no errors; 90-99=negligible issue; 75-89=strong control with clear errors;
50-74=multiple meaningful problems; 25-49=frequent errors weakening structure;
1-24=severe problems throughout; 0=invalid or no grammatically assessable response.
Judge severity rather than subtracting a fixed amount per error.

NATURALNESS: Idiomatic, conventional target-language phrasing in context: word
choice, collocations, register, expressions, and construction. Judge independently
of accuracy and grammar; fluent or grammatical wording can still be unnatural,
and natural wording can convey the wrong meaning.
Bands: 100=fully natural; 90-99=negligible awkwardness; 75-89=noticeable awkwardness
or uncommon combinations; 50-74=repeatedly unnatural/literal but understandable;
1-49=severely unnatural; 0=invalid or no assessable target-language response.

FLUENCY: Assess only acoustic delivery from the audio: rhythm, continuity, pacing,
pauses, hesitation, repetition, self-correction, and prolonged silence. Do not
infer fluency from the transcript or penalize meaning/grammar errors, accent
alone, or normal deliberate pauses.
Bands: 100=smooth, continuous and naturally paced; 90-99=negligible disruption;
75-89=occasional hesitation; 50-74=slow/cautious with interruptions;
25-49=halting with frequent/prolonged hesitation; 1-24=labored word-by-word delivery;
0=invalid or no assessable speech.

FEEDBACK AND RECOMMENDATIONS
feedback: at most five concise items in {feedback_language_name}, each identifying
one distinct actual problem, most important first. Refer to the learner's wording
when useful. No repeated issues, metric labels, praise, generic encouragement,
or invented criticism; return [] if there are no meaningful problems.
recommended_translations: one to three natural, grammatical {target_language}
translations appropriate to the CEFR level, faithfully preserving the complete
source meaning and temporal distinctions. Alternatives beyond the references
are welcome, but never recommend a translation that changes the meaning.
Keep all feedback, scores, validity, and recognized speech mutually consistent.
""".strip()


def _evaluate_audio_sync(
    exercise: Exercise,
    audio_bytes: bytes,
    mime_type: str,
    feedback_language: FeedbackLanguage,
) -> GeminiEvaluation:
    if not settings.gemini_api_key or not settings.gemini_api_key.strip():
        logger.error("GEMINI_API_KEY is not configured")
        raise EvaluationServiceError("Please retry again.")

    normalized_bytes, normalized_mime_type, _ = _normalize_audio(
        audio_bytes,
        mime_type,
    )

    target_language_code = exercise.target_language.code
    target_language_name = exercise.target_language.name

    # Step 1: Local Whisper transcription on CPU (~300ms)
    logger.info("Step 1: Running local Whisper transcription for '%s'...", target_language_name)
    raw_transcript = transcribe_audio_locally(normalized_bytes, target_language_code)
    cleaned_transcript = _clean_transcription(raw_transcript)
    logger.info("Step 1 Whisper Result: '%s'", cleaned_transcript)

    # Short-circuit: If no intelligible speech was recognized, stop immediately without calling Gemini!
    if not cleaned_transcript:
        logger.info("Short-circuiting: No speech recognized by Whisper. Returning 0 scores with ZERO Gemini calls.")
        feedback = (
            f"কোনো স্পষ্ট {exercise.target_language.bengali_name} কথা শনাক্ত করা যায়নি। দয়া করে স্পষ্টভাবে বলুন।"
            if feedback_language == "bn"
            else f"No clear {target_language_name} speech was detected. Please speak clearly and try again."
        )
        return GeminiEvaluation(
            recognized_translation="",
            is_valid_response=False,
            accuracy_score=0,
            grammar_score=0,
            naturalness_score=0,
            fluency_score=0,
            feedback=[feedback],
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
    evaluation_response = _generate_evaluation(
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
            "Please retry again."
        ) from exc


async def evaluate_audio(
    exercise: Exercise,
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
        raise EvaluationServiceError("Please retry again.") from exc
