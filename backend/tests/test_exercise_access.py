"""Public-sample and member access checks without database or Gemini requests."""
from collections import namedtuple
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from fastapi import HTTPException

from app.api.routes import evaluations, exercises
from app.models.exercise import Exercise
from app.schemas.evaluation import GeminiEvaluation


ExerciseRow = namedtuple("ExerciseRow", "exercise overall_score total_count")


class ExerciseAccessTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.source = SimpleNamespace(language_id=1, code="bn")
        self.target = SimpleNamespace(language_id=2, code="en")
        self.user = SimpleNamespace(user_id=uuid4(), native_language_id=1)
        self.session = SimpleNamespace(scalar=AsyncMock(), execute=AsyncMock())
        self.upload = SimpleNamespace(
            content_type="audio/webm", read=AsyncMock(return_value=b"recorded audio"),
            close=AsyncMock(),
        )
        self.evaluation = GeminiEvaluation(
            recognized_translation="I go to school.", is_valid_response=True,
            accuracy_score=100, grammar_score=100, naturalness_score=100,
            fluency_score=90, feedback=[], recommended_translations=["I go to school."],
        )

    def exercise(self, is_public):
        return Exercise(
            exercise_id=10, source_language_id=1, target_language_id=2,
            level="A1", title="স্কুলের দিন", source_text="PRIVATE_PROMPT_SENTINEL",
            preferred_solutions=["PRIVATE_SOLUTION_SENTINEL"],
            time_limit_seconds=10, is_public=is_public, is_active=True,
        )

    async def detail(self, current_user=None):
        with patch.object(exercises, "resolve_language_pair", return_value=(self.source, self.target)):
            return await exercises.get_exercise("bn", "en", 10, self.session, current_user)

    async def submit(self, current_user=None):
        with patch.object(evaluations, "resolve_language_pair", return_value=(self.source, self.target)):
            return await evaluations.evaluate_exercise(
                "bn", "en", 10, self.upload, "en", self.session, current_user,
            )

    async def test_guest_catalog_shows_locks_without_exposing_prompts_or_answers(self):
        for current_user in (None, self.user):
            with self.subTest(authenticated=current_user is not None):
                rows = [
                    ExerciseRow(self.exercise(True), None, 2),
                    ExerciseRow(self.exercise(False), None, 2),
                ]
                self.session.execute.return_value = SimpleNamespace(all=lambda: rows)
                with patch.object(exercises, "resolve_language_pair", return_value=(self.source, self.target)):
                    response = await exercises.list_exercises(
                        "bn", "en", self.session, current_user, None, 20, 0,
                    )
                self.assertEqual(response.total, 2)
                self.assertFalse(response.items[0].is_locked)
                self.assertEqual(response.items[0].title, "স্কুলের দিন")
                self.assertEqual(response.items[1].title, "স্কুলের দিন")
                self.assertEqual(response.items[1].is_locked, current_user is None)
                payload = response.model_dump_json()
                self.assertNotIn("PRIVATE_PROMPT_SENTINEL", payload)
                self.assertNotIn("PRIVATE_SOLUTION_SENTINEL", payload)
                self.assertNotIn("source_text", payload)
                self.assertNotIn("preferred_solutions", payload)

    async def test_guest_can_open_public_exercise(self):
        self.session.scalar.return_value = self.exercise(True)
        response = await self.detail()
        self.assertTrue(response.is_public)
        self.assertEqual(response.title, "স্কুলের দিন")
        self.assertFalse(response.is_locked)
        self.assertEqual(response.source_text, "PRIVATE_PROMPT_SENTINEL")

    async def test_guest_cannot_open_locked_exercise_by_direct_url(self):
        self.session.scalar.return_value = self.exercise(False)
        with self.assertRaises(HTTPException) as failure:
            await self.detail()
        self.assertEqual(failure.exception.status_code, 401)
        self.assertEqual(failure.exception.headers["WWW-Authenticate"], "Bearer")
        self.assertNotIn("PRIVATE_PROMPT_SENTINEL", failure.exception.detail)

    async def test_signed_in_user_can_open_locked_exercise(self):
        self.session.scalar.side_effect = [self.exercise(False), None]
        response = await self.detail(self.user)
        self.assertFalse(response.is_public)
        self.assertFalse(response.is_locked)
        self.assertEqual(response.source_text, "PRIVATE_PROMPT_SENTINEL")

    async def test_guest_cannot_evaluate_locked_exercise_by_direct_api_call(self):
        self.session.scalar.return_value = self.exercise(False)
        with (
            patch.object(evaluations, "evaluate_audio", new_callable=AsyncMock) as provider,
            patch.object(evaluations, "save_authenticated_result", new_callable=AsyncMock) as save,
            self.assertRaises(HTTPException) as failure,
        ):
            await self.submit()
        self.assertEqual(failure.exception.status_code, 401)
        provider.assert_not_awaited()
        save.assert_not_awaited()
        self.upload.read.assert_not_awaited()

    async def test_guest_can_evaluate_public_sample_without_saving_a_score(self):
        self.session.scalar.return_value = self.exercise(True)
        with (
            patch.object(evaluations, "evaluate_audio", new_callable=AsyncMock, return_value=self.evaluation) as provider,
            patch.object(evaluations, "save_authenticated_result", new_callable=AsyncMock) as save,
        ):
            response = await self.submit()
        provider.assert_awaited_once()
        save.assert_not_awaited()
        self.assertFalse(response.saved)
        self.upload.close.assert_awaited_once()

    async def test_signed_in_user_can_evaluate_locked_exercise_and_save_score(self):
        self.session.scalar.return_value = self.exercise(False)
        with (
            patch.object(evaluations, "evaluate_audio", new_callable=AsyncMock, return_value=self.evaluation) as provider,
            patch.object(evaluations, "save_authenticated_result", new_callable=AsyncMock) as save,
        ):
            response = await self.submit(self.user)
        provider.assert_awaited_once()
        save.assert_awaited_once()
        self.assertTrue(response.saved)

    async def test_invalid_speech_does_not_replace_a_saved_result(self):
        self.session.scalar.return_value = self.exercise(False)
        invalid = self.evaluation.model_copy(update={"is_valid_response": False})
        with (
            patch.object(evaluations, "evaluate_audio", new_callable=AsyncMock, return_value=invalid),
            patch.object(evaluations, "save_authenticated_result", new_callable=AsyncMock) as save,
        ):
            response = await self.submit(self.user)
        save.assert_not_awaited()
        self.assertFalse(response.saved)

    async def test_provider_failure_does_not_replace_a_saved_result(self):
        self.session.scalar.return_value = self.exercise(False)
        with (
            patch.object(evaluations, "evaluate_audio", new_callable=AsyncMock, side_effect=evaluations.EvaluationServiceError("Busy", status_code=503)),
            patch.object(evaluations, "save_authenticated_result", new_callable=AsyncMock) as save,
            self.assertRaises(HTTPException) as failure,
        ):
            await self.submit(self.user)
        self.assertEqual(failure.exception.status_code, 503)
        save.assert_not_awaited()

    async def test_inactive_or_missing_exercises_still_return_not_found(self):
        self.session.scalar.return_value = None
        with self.assertRaises(HTTPException) as detail_failure:
            await self.detail()
        self.assertEqual(detail_failure.exception.status_code, 404)
        with (
            patch.object(evaluations, "evaluate_audio", new_callable=AsyncMock) as provider,
            self.assertRaises(HTTPException) as evaluation_failure,
        ):
            await self.submit()
        self.assertEqual(evaluation_failure.exception.status_code, 404)
        provider.assert_not_awaited()

    async def test_signing_in_does_not_bypass_native_language_rules(self):
        wrong_source_user = SimpleNamespace(user_id=uuid4(), native_language_id=2)
        with self.assertRaises(HTTPException) as detail_failure:
            await self.detail(wrong_source_user)
        self.assertEqual(detail_failure.exception.status_code, 403)
        with (
            patch.object(evaluations, "evaluate_audio", new_callable=AsyncMock) as provider,
            self.assertRaises(HTTPException) as evaluation_failure,
        ):
            await self.submit(wrong_source_user)
        self.assertEqual(evaluation_failure.exception.status_code, 403)
        provider.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
