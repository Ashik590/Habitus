"""Saved-result ownership, replacement, and legacy-data checks without a database."""
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.dialects import postgresql

from app.api.routes.evaluations import get_saved_result, router, save_authenticated_result
from app.db.session import get_database_session
from app.models.exercise import Exercise
from app.models.user_exercise import UserExercise
from app.schemas.evaluation import GeminiEvaluation


class SavedResultTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.user = SimpleNamespace(user_id=uuid4())
        self.exercise = Exercise(
            exercise_id=10, title="স্কুলের দিন", level="A1",
            source_language_id=1, target_language_id=2,
            source_text="আমি স্কুলে যাই।", preferred_solutions=["I go to school."],
            time_limit_seconds=10, is_active=True, is_public=False,
        )
        self.result = UserExercise(
            user_id=self.user.user_id, exercise_id=10,
            accuracy_score=Decimal("90"), grammar_score=Decimal("80"),
            naturalness_score=Decimal("85"), fluency_score=Decimal("95"),
            overall_score=Decimal("87.25"),
            recognized_translation="I go to school.", feedback=["Speak more naturally."],
            completed_at=datetime(2026, 11, 28, 12, 0, tzinfo=timezone.utc),
        )
        self.session = SimpleNamespace(execute=AsyncMock(), commit=AsyncMock())

    async def test_review_contains_saved_details_and_current_exercise_solutions(self):
        self.session.execute.return_value = SimpleNamespace(one_or_none=lambda: (self.result, self.exercise))
        response = await get_saved_result("bn", "en", 10, self.session, self.user)
        self.assertEqual(response.feedback, ["Speak more naturally."])
        self.assertEqual(response.recognized_translation, "I go to school.")
        self.assertEqual(response.completed_at, self.result.completed_at)
        self.assertEqual(response.preferred_solutions, self.exercise.preferred_solutions)
        self.assertNotIn("recommended_translations", response.model_dump())
        self.assertNotIn("feedback_language", response.model_dump())

        statement = self.session.execute.await_args.args[0].compile(dialect=postgresql.dialect())
        # Even public exercises must be scoped to this account and language pair.
        self.assertIn("user_exercises.user_id =", str(statement))
        for value in (self.user.user_id, 10, "bn", "en"):
            self.assertIn(value, statement.params.values())

    async def test_missing_or_other_users_result_is_not_found(self):
        self.session.execute.return_value = SimpleNamespace(one_or_none=lambda: None)
        with self.assertRaises(HTTPException) as failure:
            await get_saved_result("bn", "en", 10, self.session, self.user)
        self.assertEqual(failure.exception.status_code, 404)

    async def test_legacy_scores_remain_readable_without_invented_details(self):
        self.result.recognized_translation = None
        self.result.feedback = None
        self.result.completed_at = None
        self.session.execute.return_value = SimpleNamespace(one_or_none=lambda: (self.result, self.exercise))
        response = await get_saved_result("bn", "en", 10, self.session, self.user)
        self.assertEqual(response.overall_score, 87.25)
        self.assertIsNone(response.recognized_translation)
        self.assertIsNone(response.feedback)
        self.assertIsNone(response.completed_at)

    async def test_new_valid_result_replaces_scores_and_details_together(self):
        evaluation = GeminiEvaluation(
            recognized_translation="I go to school.", is_valid_response=True,
            accuracy_score=100, grammar_score=100, naturalness_score=100,
            fluency_score=100, feedback=[], recommended_translations=["I attend school."],
        )
        await save_authenticated_result(self.session, self.user, self.exercise, evaluation, Decimal("100"))
        statement = self.session.execute.await_args.args[0].compile(dialect=postgresql.dialect())
        sql = str(statement)
        self.assertIn("ON CONFLICT (user_id, exercise_id) DO UPDATE SET", sql)
        updates = sql.split("DO UPDATE SET", 1)[1]
        for column in ("accuracy_score", "grammar_score", "naturalness_score", "fluency_score", "overall_score", "recognized_translation", "feedback", "completed_at"):
            self.assertIn(f"{column} =", updates)
        self.assertIn("clock_timestamp()", updates)
        self.assertIn("I go to school.", statement.params.values())
        self.assertIn([], statement.params.values())
        self.assertNotIn("recommended_translations", sql)
        self.session.commit.assert_awaited_once()

    def test_guest_cannot_review_even_a_public_exercise(self):
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_database_session] = lambda: self.session
        with TestClient(app) as client:
            response = client.get("/practice/bn/en/exercises/10/result")
        self.assertEqual(response.status_code, 401)
        self.session.execute.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
