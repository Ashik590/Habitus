import asyncio
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
import io
import logging
import math
import random
import re
import threading
import time
import wave

from faster_whisper import WhisperModel
from google import genai
from google.genai import errors, types
import httpx
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
        retry_after_seconds: int | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.retry_after_seconds = retry_after_seconds


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


class KeyState(str, Enum):
    AVAILABLE = "AVAILABLE"
    COOLDOWN = "COOLDOWN"
    HALF_OPEN = "HALF_OPEN"
    DISABLED = "DISABLED"


@dataclass
class KeyRecord:
    state: KeyState = KeyState.AVAILABLE
    consecutive_failures: int = 0
    cooldown_until: float | None = None
    last_failure_at: float | None = None


class GeminiKeyPool:
    """Thread-safe circuit breaker for Gemini API keys."""

    COOLDOWN_SECONDS = (60, 300, 900, 3600, 21600, 43200)

    def __init__(self) -> None:
        self._records: dict[str, KeyRecord] = {}
        self._next_key_index = 0
        self._lock = threading.Lock()

    def acquire_key(self, all_keys: list[str], excluded: set[str]) -> str | None:
        """Select one key, lazily opening a single expired cooldown for probing."""
        now = time.time()
        with self._lock:
            if not all_keys:
                return None

            start = self._next_key_index % len(all_keys)
            ordered_keys = all_keys[start:] + all_keys[:start]
            for key in ordered_keys:
                if key in excluded:
                    continue

                record = self._records.setdefault(key, KeyRecord())
                if record.state == KeyState.AVAILABLE:
                    self._next_key_index = (all_keys.index(key) + 1) % len(all_keys)
                    return key

                if (
                    record.state == KeyState.COOLDOWN
                    and record.cooldown_until is not None
                    and now >= record.cooldown_until
                ):
                    # The lock makes this an exclusive recovery probe. Other
                    # requests see HALF_OPEN and bypass the same key.
                    record.state = KeyState.HALF_OPEN
                    self._next_key_index = (all_keys.index(key) + 1) % len(all_keys)
                    return key

            return None

    def mark_success(self, key: str) -> None:
        with self._lock:
            self._records[key] = KeyRecord()

    def mark_rate_limited(self, key: str, provider_retry_after: float | None) -> None:
        now = time.time()
        with self._lock:
            record = self._records.setdefault(key, KeyRecord())
            record.consecutive_failures += 1
            schedule_index = min(
                record.consecutive_failures - 1,
                len(self.COOLDOWN_SECONDS) - 1,
            )
            cooldown_seconds = float(self.COOLDOWN_SECONDS[schedule_index])
            if provider_retry_after is not None:
                cooldown_seconds = max(cooldown_seconds, provider_retry_after)

            record.state = KeyState.COOLDOWN
            record.last_failure_at = now
            record.cooldown_until = now + cooldown_seconds
            masked = f"...{key[-4:]}" if len(key) >= 4 else "..."
            logger.warning(
                "Gemini key %s entered cooldown for %.0fs after consecutive 429 #%d.",
                masked,
                cooldown_seconds,
                record.consecutive_failures,
            )

    def release_probe(self, key: str) -> None:
        """Return a half-open key after a failure unrelated to its quota."""
        with self._lock:
            record = self._records.setdefault(key, KeyRecord())
            if record.state == KeyState.HALF_OPEN:
                record.state = KeyState.AVAILABLE
                record.cooldown_until = None

    def disable(self, key: str) -> None:
        with self._lock:
            record = self._records.setdefault(key, KeyRecord())
            record.state = KeyState.DISABLED
            record.cooldown_until = None
            record.last_failure_at = time.time()

    def retry_after_seconds(self, all_keys: list[str]) -> int | None:
        now = time.time()
        with self._lock:
            future_cooldowns = [
                record.cooldown_until
                for key in all_keys
                if (record := self._records.get(key)) is not None
                and record.state == KeyState.COOLDOWN
                and record.cooldown_until is not None
                and record.cooldown_until > now
            ]
        if not future_cooldowns:
            return None
        return max(1, math.ceil(min(future_cooldowns) - now))


_key_pool = GeminiKeyPool()

TRANSIENT_STATUS_CODES = {500, 502, 503, 504}
REQUEST_ERROR_STATUS_CODES = {400, 404, 422}
MAX_TRANSIENT_RETRIES = 2


def _find_retry_delay(value: object) -> float | None:
    """Best-effort extraction; circuit-breaker correctness does not depend on it."""
    if isinstance(value, dict):
        for key, child in value.items():
            if key.lower() in {"retrydelay", "retry_delay"}:
                match = re.search(r"([0-9]+(?:\.[0-9]+)?)", str(child))
                if match:
                    return float(match.group(1))
            found = _find_retry_delay(child)
            if found is not None:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _find_retry_delay(child)
            if found is not None:
                return found
    return None


def _send_gemini_request(
    client: genai.Client,
    contents: list[object] | object,
    temperature: float,
):
    return client.models.generate_content(
        model=settings.gemini_model,
        contents=contents,
        config=types.GenerateContentConfig(
            temperature=temperature,
            response_mime_type="application/json",
            response_schema=GeminiEvaluation,
            http_options=types.HttpOptions(
                timeout=30_000,
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        ),
    )


def _generate_with_key_pool(
    contents: list[object] | object,
    temperature: float = 0.0,
):
    all_keys = settings.all_gemini_api_keys
    if not all_keys:
        raise EvaluationServiceError("No Gemini API key is configured.")

    attempted_keys: set[str] = set()
    while api_key := _key_pool.acquire_key(all_keys, attempted_keys):
        attempted_keys.add(api_key)
        masked_key = f"...{api_key[-4:]}" if len(api_key) >= 4 else "..."
        client = genai.Client(api_key=api_key)

        for transient_attempt in range(MAX_TRANSIENT_RETRIES + 1):
            try:
                response = _send_gemini_request(client, contents, temperature)
                _key_pool.mark_success(api_key)
                logger.info(
                    "Gemini evaluation succeeded using API key %s with model %s",
                    masked_key,
                    settings.gemini_model,
                )
                return response

            except errors.ClientError as exc:
                if exc.code == 429:
                    _key_pool.mark_rate_limited(
                        api_key,
                        provider_retry_after=_find_retry_delay(exc.details),
                    )
                    break

                _key_pool.release_probe(api_key)
                if exc.code in {401, 403}:
                    _key_pool.disable(api_key)
                    logger.error(
                        "Gemini key %s was disabled after provider error %s.",
                        masked_key,
                        exc.code,
                    )
                    break

                if exc.code in REQUEST_ERROR_STATUS_CODES:
                    logger.exception("Gemini rejected the evaluation request")
                    raise EvaluationServiceError(
                        "The evaluation provider rejected the request.",
                        status_code=502,
                    ) from exc

                logger.exception("Gemini returned an unexpected client error")
                raise EvaluationServiceError(
                    "The evaluation provider could not process the request.",
                    status_code=502,
                ) from exc

            except errors.ServerError as exc:
                if exc.code not in TRANSIENT_STATUS_CODES:
                    _key_pool.release_probe(api_key)
                    logger.exception("Gemini returned an unexpected server error")
                    raise EvaluationServiceError(
                        "The evaluation provider returned an unexpected error."
                    ) from exc

                if transient_attempt < MAX_TRANSIENT_RETRIES:
                    delay = (2**transient_attempt) + random.uniform(0, 0.5)
                    logger.warning(
                        "Gemini transient error %s for key %s; retrying in %.2fs.",
                        exc.code,
                        masked_key,
                        delay,
                    )
                    time.sleep(delay)
                    continue

                _key_pool.release_probe(api_key)
                raise EvaluationServiceError(
                    "The evaluation service is temporarily unavailable. Please try again.",
                    retry_after_seconds=5,
                ) from exc

            except (httpx.TimeoutException, httpx.TransportError) as exc:
                if transient_attempt < MAX_TRANSIENT_RETRIES:
                    delay = (2**transient_attempt) + random.uniform(0, 0.5)
                    logger.warning(
                        "Gemini transport failure for key %s; retrying in %.2fs.",
                        masked_key,
                        delay,
                    )
                    time.sleep(delay)
                    continue

                _key_pool.release_probe(api_key)
                raise EvaluationServiceError(
                    "The evaluation service timed out. Please try again.",
                    retry_after_seconds=5,
                ) from exc

    retry_after = _key_pool.retry_after_seconds(all_keys)
    raise EvaluationServiceError(
        "Evaluation capacity is temporarily unavailable. Please try again later.",
        retry_after_seconds=retry_after,
    )


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
You are a strict, impartial language examiner evaluating a learner's
spoken {target_language} translation of a Bengali sentence.

CORE EXAMINER PRINCIPLE:
Evaluate the learner's actual response objectively. Do not inflate
scores out of politeness or award grace points because the response
is understandable.

Use the full 0-100 scoring scale meaningfully. Scores must reflect
the actual quality of the response according to the criteria below.

Evaluate each scoring dimension independently. Do not allow a high
or low score in one dimension to automatically influence another.

SOURCE SENTENCE:
{exercise.bengali_text}

CEFR LEVEL:
{exercise.level}

REFERENCE TRANSLATIONS:
{references}

Reference translations are guidance, not mandatory answers.
Other valid translations must receive appropriate scores.

The learner's speech was initially transcribed by speech recognition as:
"{transcribed_text}"


==================================================
1. TRANSCRIPT REFINEMENT AND VERIFICATION
==================================================

Listen carefully to the attached audio recording.

Use the speech recognition transcript as an initial acoustic reference,
but independently verify the actual words spoken by the learner.

Correct minor speech-recognition errors by listening to the recording.
Do not invent words, silently improve the learner's sentence, or
replace the learner's response with a reference translation.

In "recognized_translation", provide the actual words articulated
by the learner in {target_language}, preserving their original meaning
and wording as accurately as possible.

Do not correct the learner's grammatical errors in this field.
Do not replace incorrect words with the words the learner should have
said.

If the recording is unclear, use the available acoustic evidence
and transcript conservatively rather than hallucinating speech.


==================================================
2. RESPONSE VALIDITY
==================================================

Determine whether the learner has made a genuine attempt to translate
the source sentence into {target_language}.

Set "is_valid_response" to true if the response constitutes a genuine
translation attempt, even if it contains substantial semantic errors,
missing information, grammatical errors, or incorrect vocabulary.

Set it to false only if the response is completely unrelated,
meaningless, or constitutes a refusal or a non-attempt to translate.

An incorrect translation is still a valid translation attempt.

If "is_valid_response" is false, set all four dimension scores to 0:
accuracy_score, grammar_score, naturalness_score, and fluency_score.

If true, evaluate all dimensions according to their respective rules.


==================================================
3. ACCURACY SCORE — SEMANTIC FIDELITY
==================================================

Definition:
Accuracy measures whether the complete meaning conveyed by the learner
is semantically equivalent to the complete meaning of the source.

Apply this criterion strictly. Full accuracy requires preservation of
the whole source meaning. Missing information, additional information,
substituted information, contradictions, and altered relationships must
all reduce the score according to their semantic importance.

Judge the meaning actually conveyed, not merely the presence of
overlapping words or individual concepts.

Evaluate the following aspects:

A. Semantic fidelity:
Determine whether the learner preserves the intended meaning of
the source, including its central facts, relationships, actions,
participants, objects, and circumstances.

B. Lexical fidelity:
Determine whether the chosen words and expressions represent the
intended source concepts accurately. Penalize substitutions that
change the intended meaning.

C. Temporal and aspectual fidelity:
Determine whether the learner preserves the temporal meaning of
the source, including tense, aspect, habituality, continuity,
completion, repetition, and futurity where applicable.

A grammatically correct sentence can still be semantically inaccurate
if it changes the temporal situation described by the source.

D. Semantic contradictions:
Identify whether the learner's response introduces claims that
contradict or materially alter the meaning of the source.

E. Additions and omissions:
Identify every meaningful source detail that was omitted and every
meaningful claim, qualification, relationship, or circumstance that
the learner added. Both omissions and additions reduce semantic
equivalence and therefore reduce accuracy.

The presence of some matching words, participants, or objects does not
make a response accurate when they occur inside a different action,
state, relationship, or central proposition. Judge the proposition as
a whole rather than awarding credit for isolated lexical overlap.

SCORING GUIDELINES:

100: Complete semantic equivalence. No meaningful information is
missing, added, substituted, contradicted, or altered.

90-99: Nearly equivalent, but an extremely small semantic nuance is
missing, added, or altered. Do not use this range for a clearly
different property, relationship, action, state, time, or condition.

70-89: Much of the intended meaning is preserved, but at least one
meaningful detail is missing, added, substituted, or altered.

40-69: A major component, relationship, action, state, qualification,
or other important part of the source meaning is wrong or missing.

1-39: The central meaning is substantially different. Only fragments
of the source meaning correspond, even if several words or participants
overlap.

0: No meaningful semantic correspondence exists, or the response
is invalid under the response-validity rules.

These ranges are guidance, not rigid scoring formulas. Select the
score that best reflects the actual semantic fidelity of the response.

Accuracy includes both correctness and complete semantic coverage.
Every meaningful omission belongs in the accuracy judgment, as does
every addition, substitution, distortion, or contradiction.

When a temporal or aspectual change alters the meaning of the source,
penalize accuracy according to the severity of that change. Do not
automatically treat every tense difference as minor.

Evaluate the intended meaning in context rather than comparing
grammatical forms mechanically. Different grammatical constructions
may express the same meaning, and identical grammatical tenses
may express different meanings depending on context.


==================================================
4. STRICT ACCURACY COVERAGE RULES
==================================================

Accuracy must account for every meaningful part of the source, not
only its general topic or a collection of matching words.

STEP 1: DECOMPOSE THE SOURCE SENTENCE

Independently identify its meaningful semantic units.

Depending on the sentence, these may include:
- Subject or participant
- Action or predicate
- Object or destination
- Time and frequency
- Location
- Negation
- Conditions
- Modifiers
- Relationships between concepts
- Habitual, ongoing, completed, or other temporal information
- Other meaningful details required to preserve the source message

Do not count words mechanically. A single expression may convey
multiple semantic units, while multiple words may convey one unit.

STEP 2: DETERMINE THE IMPORTANCE OF EACH UNIT

Distinguish between major and minor semantic units.

Major units carry central information necessary to understand
the intended message.

Minor units contribute supplementary details or nuances whose
absence does not substantially affect the central message.

Determine importance according to the actual source sentence and
its context. Do not assume every unit has equal importance.

STEP 3: IDENTIFY WHAT WAS FAITHFULLY CONVEYED

Determine which source semantic units are expressed in the learner's
response, even if they are expressed using different but valid wording.

Do not require the learner to use the exact words or structure of
the reference translations.

Consider a source unit conveyed when its intended information is
communicated, not merely when a related word appears in the response.

A source concept that is completely omitted should count as missing.

If the learner replaces a source concept with a different concept,
the source information is missing and different information has been
introduced. Treat that as a serious loss of semantic equivalence.

STEP 4: DETERMINE THE ACCURACY SCORE

Judge the degree of semantic equivalence using both the proportion and
relative importance of the source information faithfully conveyed.
This is not an instruction to count words or assign equal importance
to every unit.

Major omissions must cause substantially greater reductions than
minor omissions.

Missing or changing a central action, state, participant, relationship,
destination, or other essential unit must substantially reduce accuracy.

Missing a minor detail should cause a comparatively small reduction.

Do not assign the same penalty to every difference. Consider the
semantic importance of what is missing, added, substituted, or changed.

Accuracy must reflect the meaning actually communicated, not the
grammatical quality, fluency, or naturalness of the response.

If the entire source meaning is faithfully conveyed, accuracy can be
high even if the learner's wording is grammatically awkward.

If only a small portion of the source meaning is faithfully conveyed,
accuracy must be low even if that portion is grammatically perfect.

Do not force an exact numerical result from an arbitrary number of
semantic units. Use the identified units, their importance, and the
extent of coverage to make a consistent, evidence-based judgment.


==================================================
5. GRAMMAR SCORE — TARGET-LANGUAGE MORPHOSYNTAX
==================================================

Definition:
Grammar measures the grammatical correctness of the sentence
actually produced by the learner.

Evaluate the grammatical structure according to the formal rules
of {target_language}.

Consider relevant features such as:
- Sentence structure and word order
- Verb conjugation and verb forms
- Tense and aspect construction
- Subject-verb agreement
- Noun-adjective agreement
- Articles and determiners
- Preposition usage and governance
- Pronouns and case
- Clause structure
- Other applicable grammatical rules

Evaluate the learner's actual sentence, not the sentence they
should have produced.

Do not require the learner to follow the structure of a reference
translation if their own construction is grammatically valid.

Do not penalize grammatical correctness merely because the learner
uses different vocabulary or phrasing from the reference translation.

Distinguish grammatical errors from semantic errors.

A sentence may be grammatically correct while expressing the wrong
meaning. In such cases, grammar may remain high while accuracy
is reduced.

A sentence may also convey the intended meaning despite grammatical
errors. In such cases, judge grammar according to the actual
grammatical violations.

Do not penalize pauses, hesitation sounds, repetitions, or momentary
stutters as grammatical errors when the underlying construction
is grammatically valid.

These speech-delivery characteristics belong under fluency.

SCORING GUIDELINES:

100: Fully grammatical, with no grammatical errors.

90-99: Nearly flawless grammar, with only a negligible issue.

75-89: Strong grammatical control, but with one or more clear errors.

50-74: Multiple meaningful grammatical problems.

25-49: Frequent grammatical errors that substantially weaken
sentence structure.

1-24: Severe grammatical problems throughout the response.

0: Apply only when required by the invalid-response rules or when
no grammatically assessable target-language response is produced.

Use the full scale proportionately. Do not mechanically subtract
a fixed number of points for every error without considering
its severity and effect on grammatical correctness.


==================================================
6. NATURALNESS SCORE — IDIOMATIC AUTHENTICITY
==================================================

Definition:
Naturalness measures how natural, idiomatic, and conventional
the learner's translation sounds to a proficient speaker of
{target_language} in the given context.

Evaluate whether the phrasing reflects natural usage rather than
awkward, overly literal, or unidiomatic language.

Consider:
- Idiomatic phrasing
- Word choice and collocations
- Natural word combinations
- Appropriate register and tone
- Conventional expressions
- Natural sentence construction
- Whether the phrasing sounds appropriate in context

Accept different valid translations, including translations that
use a different structure from the reference translations.

Do not confuse naturalness with grammatical correctness.

A sentence can be grammatically correct but sound unnatural,
overly literal, or stylistically awkward.

A sentence can also sound natural and fluent while conveying
the wrong meaning.

Do not automatically award a high naturalness score merely because
a sentence is accurate or grammatically correct.

Likewise, do not automatically lower naturalness because the
translation differs from the reference translation.

Evaluate naturalness independently of accuracy.

SCORING GUIDELINES:

100: Fully natural, idiomatic, conventional, and contextually
appropriate phrasing for proficient speakers.

90-99: Highly natural, with only negligible awkwardness.

75-89: Generally natural, but with clearly noticeable awkwardness or
an uncommon word combination.

50-74: Understandable but repeatedly unnatural, overly literal, or
stylistically unusual.

1-49: Severely unnatural phrasing that makes the sentence difficult
to interpret as conventional target-language usage.

0: Apply only when required by the invalid-response rules or when
no assessable target-language response is produced.


==================================================
7. FLUENCY SCORE — ACOUSTIC DELIVERY
==================================================

Definition:
Fluency measures how smoothly and continuously the learner speaks.
Evaluate it exclusively from the audio recording.

Assess:
- Speech rhythm and cadence
- Continuity of delivery
- Frequency and duration of pauses
- Hesitation frequency
- Prolonged silences
- Repetitions and self-corrections
- Temporal pacing
- Overall smoothness of spoken delivery

Do not evaluate fluency from the written transcript alone.

Do not penalize the learner's fluency because their translation
is inaccurate, grammatically incorrect, or unnatural.

Do not penalize accent differences by themselves, provided the
speech delivery remains assessable.

Do not confuse deliberate, natural pauses with excessive hesitation.
Evaluate the overall pattern of speech rather than counting every
pause as an error.

SCORING GUIDELINES:

100: Fully smooth, continuous, naturally paced delivery without
meaningful hesitation or disruption.

90-99: Highly fluent delivery with only negligible disruption.

75-89: Steady delivery with brief or occasional noticeable hesitation.

50-74: Noticeably slow, cautious, or deliberate delivery, with
some interruptions to the flow.

25-49: Halting, fragmented delivery with frequent or prolonged
hesitations.

1-24: Highly labored, word-by-word delivery with extensive
interruptions or prolonged silences.

0: Apply only when required by the invalid-response rules or when
the audio provides no assessable speech.

Base the score on the actual audio evidence, not assumptions about
the learner's speaking ability.


==================================================
8. INDEPENDENCE OF SCORING DIMENSIONS
==================================================

The four dimensions evaluate different aspects of performance.

Accuracy: Is the conveyed meaning faithful to the source?

Grammar: Is the learner's sentence grammatically correct?

Naturalness: Does the translation sound idiomatic and natural?

Fluency: How smoothly does the learner speak?

Do not use one dimension as a substitute for another.

In particular:
- Do not lower grammar solely because meaning is incorrect.
- Do not lower fluency solely because grammar is incorrect.
- Do not lower naturalness solely because meaning is inaccurate.
- Do not award high accuracy simply because the response contains
  several correct words.
- Do not award high naturalness simply because the response is
  fluent or grammatically correct.

An individual error may legitimately affect multiple dimensions only
when it independently affects the separate property measured by each
dimension. Do not transfer an accuracy penalty automatically into
grammar, naturalness, or fluency.

Use independent judgment for every score.


==================================================
9. FEEDBACK AND RECOMMENDATIONS
==================================================

FEEDBACK:

Return "feedback" as a list containing only the problems identified in
the learner's response, written in {feedback_language_name}.

Each list item must identify one distinct, specific problem. Keep every
item concise and understandable. Refer to the learner's actual wording
when that helps explain the problem.

Order the problems from most important to least important. Do not repeat
the same underlying problem in multiple items. Do not organize the list
by scoring dimension, add metric labels, include generic encouragement,
or add praise. Return no more than five items.

Make every identified problem consistent with the recognized speech and
the assigned scores. If there are no meaningful problems, return an
empty list rather than inventing criticism.

RECOMMENDED TRANSLATIONS:

Provide 1 to 3 recommended translations in {target_language}.

Each recommendation must faithfully convey the source meaning and
preserve its important semantic and temporal distinctions.

Prefer natural, grammatically correct translations appropriate
to the source sentence's CEFR level.

Multiple valid translations are acceptable. Do not restrict the
recommendations to the supplied reference translations.

Do not present a translation that changes the source meaning as
a correct recommendation.


==================================================
10. OUTPUT FORMAT
==================================================

Return the evaluation using the provided response schema.
Ensure the feedback, recognized translation, response validity, and
dimension scores are mutually consistent.
""".strip()


def _evaluate_audio_sync(
    exercise: SpeakingExercise,
    audio_bytes: bytes,
    mime_type: str,
    feedback_language: FeedbackLanguage,
) -> GeminiEvaluation:
    if not settings.all_gemini_api_keys:
        raise EvaluationServiceError("No Gemini API key is configured.")

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
    evaluation_response = _generate_with_key_pool(
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
