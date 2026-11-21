"""Offline checks: provider failures must never trigger a second HTTP request."""
import json
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


class SingleGeminiRequestTests(unittest.TestCase):
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
        ):
            return evaluation._generate_evaluation("Evaluate this recording.")

    def test_provider_errors_are_not_retried(self):
        for code in (400, 403, 404, 422, 429, 500, 503, 504):
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

    def test_network_timeout_is_not_retried(self):
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
        self.assertEqual(len(requests), 1)

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


if __name__ == "__main__":
    unittest.main()
