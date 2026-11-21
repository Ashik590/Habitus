"""Offline checks for bounded retries and audio-only Gemini evaluation."""
import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from google import genai
import httpx

from app.services import gemini_evaluation as evaluation


REAL_CLIENT = genai.Client
VALID_EVALUATION = {
    "recognized_translation": "I go to school.",
    "is_valid_response": True,
    "accuracy_score": 100,
    "grammar_score": 100,
    "naturalness_score": 100,
    "fluency_score": 90,
    "feedback": [],
    "recommended_translations": ["I go to school."],
}


class GeminiRetryTests(unittest.TestCase):
    def call_with_transport(self, handler):
        """Exercise the real SDK retry policy with an in-memory HTTP transport."""
        def create_client(**kwargs):
            options = kwargs["http_options"].model_copy(update={
                "httpx_client": httpx.Client(transport=httpx.MockTransport(handler)),
            })
            return REAL_CLIENT(
                api_key=kwargs["api_key"],
                vertexai=False,
                http_options=options,
            )

        with (
            patch.object(evaluation.settings, "gemini_api_key", "offline-test-key"),
            patch.object(evaluation.genai, "Client", side_effect=create_client),
            patch("time.sleep", return_value=None),
        ):
            return evaluation._generate_evaluation("Evaluate this recording.")

    def test_permanent_and_rate_limit_errors_are_not_retried(self):
        for code in (400, 401, 403, 404, 422, 429):
            with self.subTest(status_code=code):
                requests = []

                def handler(request):
                    requests.append(request)
                    return httpx.Response(code, json={
                        "error": {"code": code, "message": "Simulated provider error"},
                    })

                with (
                    self.assertLogs(evaluation.logger, level="ERROR"),
                    self.assertRaises(evaluation.EvaluationServiceError) as failure,
                ):
                    self.call_with_transport(handler)

                self.assertEqual(str(failure.exception), "Please retry again.")
                self.assertEqual(len(requests), 1)

    def test_network_timeout_is_retried_only_once(self):
        requests = []

        def handler(request):
            requests.append(request)
            raise httpx.ReadTimeout("Simulated timeout", request=request)

        with (
            self.assertLogs(evaluation.logger, level="ERROR"),
            self.assertRaises(evaluation.EvaluationServiceError) as failure,
        ):
            self.call_with_transport(handler)

        self.assertEqual(str(failure.exception), "Please retry again.")
        self.assertEqual(len(requests), 2)

    def test_temporary_errors_are_retried_only_once(self):
        for code in (408, 500, 502, 503, 504):
            with self.subTest(status_code=code):
                requests = []

                def handler(request):
                    requests.append(request)
                    return httpx.Response(code, json={
                        "error": {"code": code, "message": "Temporary failure"},
                    })

                with (
                    self.assertLogs(evaluation.logger, level="ERROR"),
                    self.assertRaises(evaluation.EvaluationServiceError) as failure,
                ):
                    self.call_with_transport(handler)

                self.assertEqual(str(failure.exception), "Please retry again.")
                self.assertEqual(len(requests), 2)

    def test_retry_can_recover_after_a_gateway_timeout(self):
        requests = []

        def handler(request):
            requests.append(request)
            if len(requests) == 1:
                return httpx.Response(504, json={
                    "error": {"code": 504, "message": "Deadline exceeded"},
                })
            return httpx.Response(200, json={
                "candidates": [{
                    "content": {
                        "role": "model",
                        "parts": [{"text": json.dumps(VALID_EVALUATION)}],
                    },
                    "finishReason": "STOP",
                }],
            })

        response = self.call_with_transport(handler)
        self.assertEqual(json.loads(response.text), VALID_EVALUATION)
        self.assertEqual(len(requests), 2)

    def test_success_returns_response_after_one_request(self):
        requests = []

        def handler(request):
            requests.append(request)
            return httpx.Response(200, json={
                "candidates": [{
                    "content": {
                        "role": "model",
                        "parts": [{"text": json.dumps(VALID_EVALUATION)}],
                    },
                    "finishReason": "STOP",
                }],
            })

        response = self.call_with_transport(handler)
        self.assertEqual(json.loads(response.text), VALID_EVALUATION)
        self.assertEqual(len(requests), 1)

    def test_missing_key_does_not_call_provider(self):
        with (
            patch.object(evaluation.settings, "gemini_api_key", None),
            patch.object(evaluation.genai, "Client") as client,
            self.assertLogs(evaluation.logger, level="ERROR"),
            self.assertRaises(evaluation.EvaluationServiceError),
        ):
            evaluation._generate_evaluation("Evaluate this recording.")
        client.assert_not_called()


class GeminiAudioEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.exercise = SimpleNamespace(
            exercise_id=1,
            source_language=SimpleNamespace(name="Bengali"),
            target_language=SimpleNamespace(name="English"),
            source_text="আমি স্কুলে যাই।",
            preferred_solutions=["REFERENCE_ONLY_SENTINEL_DO_NOT_SEND"],
            level="A1",
        )

    def evaluate_recording(self, response=VALID_EVALUATION):
        with (
            patch.object(evaluation.settings, "gemini_api_key", "offline-test-key"),
            patch.object(evaluation, "_normalize_audio", return_value=(b"audio", "audio/wav", "wav")),
            patch.object(evaluation, "_generate_evaluation", return_value=SimpleNamespace(
                text=json.dumps(response),
            )) as generate,
        ):
            result = evaluation._evaluate_audio_sync(
                self.exercise, b"recording", "audio/webm", "en",
            )
        generate.assert_called_once()
        contents = generate.call_args.kwargs["contents"]
        self.assertEqual(len(contents), 2)
        self.assertEqual(contents[0].inline_data.data, b"audio")
        return result, contents[1]

    def test_request_includes_audio_and_source_but_not_preferred_solutions(self):
        result, prompt = self.evaluate_recording()
        self.assertIn(self.exercise.source_text, prompt)
        self.assertNotIn(self.exercise.preferred_solutions[0], prompt)
        self.assertNotIn("BROWSER TRANSCRIPT", prompt)
        self.assertEqual(result.recognized_translation, "I go to school.")

    def test_changing_stored_solutions_does_not_change_the_prompt(self):
        original = evaluation.build_evaluation_prompt(self.exercise, "en")
        self.exercise.preferred_solutions = ["A completely different answer."]
        self.assertEqual(original, evaluation.build_evaluation_prompt(self.exercise, "en"))

    def test_unrelated_speech_returned_by_gemini_is_not_replaced(self):
        response = {
            **VALID_EVALUATION,
            "recognized_translation": "Bananas are yellow.",
            "is_valid_response": False,
            "accuracy_score": 0,
            "grammar_score": 0,
            "naturalness_score": 0,
            "fluency_score": 0,
            "feedback": ["The response is unrelated to the assigned sentence."],
        }
        result, _ = self.evaluate_recording(response)
        self.assertFalse(result.is_valid_response)
        self.assertEqual(result.recognized_translation, "Bananas are yellow.")
        self.assertEqual(result.accuracy_score, 0)

    def test_silence_can_return_invalid_without_a_local_model(self):
        response = {
            **VALID_EVALUATION,
            "recognized_translation": "",
            "is_valid_response": False,
            "accuracy_score": 0,
            "grammar_score": 0,
            "naturalness_score": 0,
            "fluency_score": 0,
            "feedback": ["No intelligible speech was detected."],
        }
        result, _ = self.evaluate_recording(response)
        self.assertFalse(result.is_valid_response)
        self.assertEqual(result.fluency_score, 0)

    def test_empty_recognition_cannot_receive_positive_scores(self):
        for recognized in ("", "   ", "\t\n"):
            with self.subTest(recognized=recognized):
                # Simulate a contradictory model response: no words but valid
                # and perfect scores. Validation must block positive scores.
                response = {
                    **VALID_EVALUATION,
                    "recognized_translation": recognized,
                    "is_valid_response": True,
                    "accuracy_score": 100,
                    "grammar_score": 100,
                    "naturalness_score": 100,
                    "fluency_score": 100,
                }
                result, _ = self.evaluate_recording(response)
                self.assertEqual(result.recognized_translation, "")
                self.assertFalse(result.is_valid_response)
                for dimension in ("accuracy", "grammar", "naturalness", "fluency"):
                    self.assertEqual(getattr(result, f"{dimension}_score"), 0)

    def test_invalid_speech_cannot_keep_positive_scores(self):
        response = {
            **VALID_EVALUATION,
            "recognized_translation": "Bananas are yellow.",
            "is_valid_response": False,
        }
        result, _ = self.evaluate_recording(response)
        self.assertEqual(result.recognized_translation, "Bananas are yellow.")
        for dimension in ("accuracy", "grammar", "naturalness", "fluency"):
            self.assertEqual(getattr(result, f"{dimension}_score"), 0)

    def test_audible_grammar_errors_are_preserved(self):
        response = {
            **VALID_EVALUATION,
            "recognized_translation": "I goes to school.",
            "grammar_score": 40,
        }
        result, _ = self.evaluate_recording(response)
        self.assertTrue(result.is_valid_response)
        self.assertEqual(result.recognized_translation, "I goes to school.")
        self.assertEqual(result.grammar_score, 40)


if __name__ == "__main__":
    unittest.main()
