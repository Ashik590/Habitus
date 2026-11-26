"""Account validation and authentication checks without connecting to a database."""
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

from fastapi import HTTPException, Response
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from app.api.routes import auth, users
from app.models.language import Language
from app.models.user import User
from app.schemas.auth import AccessTokenResponse, LoginRequest
from app.schemas.user import PracticeLanguagesUpdate, UserRegister, UserResponse


REGISTRATION = {
    "name": "Md Azizul Hakim",
    "username": "ashik_590",
    "password": "test-password-only",
    "native_language_code": "bn",
    "target_language_code": "en",
}


def language(language_id, code, name):
    return Language(
        language_id=language_id, code=code, name=name,
        bengali_name=name, is_active=True,
    )


class AccountValidationTests(unittest.TestCase):
    def test_email_can_be_omitted_or_blank(self):
        self.assertIsNone(UserRegister(**REGISTRATION).email)
        for email in (None, "", "   "):
            with self.subTest(email=email):
                self.assertIsNone(UserRegister(**REGISTRATION, email=email).email)

    def test_supplied_email_must_be_valid(self):
        with self.assertRaises(ValidationError):
            UserRegister(**REGISTRATION, email="not-an-email")
        self.assertEqual(
            UserRegister(**REGISTRATION, email=" ASHIK@EXAMPLE.COM ").email,
            "ashik@example.com",
        )

    def test_username_is_case_insensitive_and_rejects_invalid_characters(self):
        registration = UserRegister(**{**REGISTRATION, "username": " Ashik_590 "})
        self.assertEqual(registration.username, "ashik_590")
        for username in ("ab", "1ashik", "ashik.name", "ashik@example.com", "a b", "a" * 31):
            with self.subTest(username=username), self.assertRaises(ValidationError):
                UserRegister(**{**REGISTRATION, "username": username})

    def test_full_name_username_password_and_both_languages_are_required(self):
        for field in REGISTRATION:
            with self.subTest(field=field), self.assertRaises(ValidationError):
                UserRegister(**{key: value for key, value in REGISTRATION.items() if key != field})

    def test_identical_languages_are_rejected_after_normalization(self):
        with self.assertRaises(ValidationError):
            UserRegister(**{**REGISTRATION, "target_language_code": " BN "})
        with self.assertRaises(ValidationError):
            PracticeLanguagesUpdate(native_language_code="bn", target_language_code=" BN ")

    def test_login_normalizes_username_without_changing_password(self):
        login = LoginRequest(username=" ASHIK_590 ", password=" PassWord ")
        self.assertEqual(login.username, "ashik_590")
        self.assertEqual(login.password, " PassWord ")

    def test_email_is_not_accepted_as_a_login_username(self):
        with self.assertRaises(ValidationError):
            LoginRequest(username="ashik@example.com", password="test-password-only")
        with self.assertRaises(ValidationError):
            LoginRequest(email="ashik@example.com", password="test-password-only")


class AccountRouteTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.native = language(1, "bn", "Bengali")
        self.target = language(2, "en", "English")
        self.session = SimpleNamespace(
            scalar=AsyncMock(), scalars=AsyncMock(), add=Mock(),
            commit=AsyncMock(), rollback=AsyncMock(), refresh=AsyncMock(),
        )

    async def test_registration_without_email_saves_username_and_language_pair(self):
        self.session.scalar.side_effect = [None, self.native, self.target]
        with patch.object(auth, "hash_password", return_value="hashed-password"):
            user = await auth.register_user(UserRegister(**REGISTRATION), self.session)
        self.assertEqual(user.username, "ashik_590")
        self.assertIsNone(user.email)
        self.assertEqual(user.native_language_id, 1)
        self.assertEqual(user.target_language_id, 2)
        self.assertEqual(user.password_hash, "hashed-password")
        self.session.add.assert_called_once_with(user)
        self.session.commit.assert_awaited_once()
        self.session.refresh.assert_awaited_once_with(user, ["native_language", "target_language"])

    async def test_duplicate_username_is_rejected_without_creating_an_account(self):
        self.session.scalar.return_value = uuid4()
        with self.assertRaises(HTTPException) as failure:
            await auth.register_user(UserRegister(**REGISTRATION), self.session)
        self.assertEqual(failure.exception.status_code, 409)
        self.assertIn("username", failure.exception.detail)
        self.session.add.assert_not_called()

    async def test_duplicate_optional_email_is_rejected(self):
        self.session.scalar.side_effect = [None, uuid4()]
        with self.assertRaises(HTTPException) as failure:
            await auth.register_user(
                UserRegister(**REGISTRATION, email="ashik@example.com"), self.session,
            )
        self.assertEqual(failure.exception.status_code, 409)
        self.assertIn("email", failure.exception.detail)
        self.session.add.assert_not_called()

    async def test_unavailable_target_language_is_rejected(self):
        self.session.scalar.side_effect = [None, self.native, None]
        with self.assertRaises(HTTPException) as failure:
            await auth.register_user(UserRegister(**REGISTRATION), self.session)
        self.assertEqual(failure.exception.status_code, 422)
        self.session.add.assert_not_called()

    async def test_concurrent_registration_conflict_rolls_back(self):
        self.session.scalar.side_effect = [None, self.native, self.target]
        self.session.commit.side_effect = IntegrityError("INSERT", {}, Exception("duplicate"))
        with (
            patch.object(auth, "hash_password", return_value="hashed-password"),
            self.assertRaises(HTTPException) as failure,
        ):
            await auth.register_user(UserRegister(**REGISTRATION), self.session)
        self.assertEqual(failure.exception.status_code, 409)
        self.session.rollback.assert_awaited_once()

    async def test_username_login_issues_a_session(self):
        user = User(user_id=uuid4(), password_hash="hashed-password", is_active=True)
        self.session.scalar.return_value = user
        with (
            patch.object(auth, "verify_password", return_value=True),
            patch.object(auth, "set_refresh_cookie") as cookie,
            patch.object(auth, "build_access_token", return_value=AccessTokenResponse(access_token="test-token")),
        ):
            response = Response()
            token = await auth.login(
                LoginRequest(username="ASHIK_590", password="test-password-only"),
                response, self.session,
            )
            self.assertEqual(token.access_token, "test-token")
            cookie.assert_called_once_with(response, user.user_id)
            criterion = self.session.scalar.call_args.args[0].whereclause
            self.assertEqual(criterion.left.key, "username")
            self.assertEqual(criterion.right.value, "ashik_590")

    async def test_bad_credentials_do_not_issue_a_session(self):
        for user in (None, User(user_id=uuid4(), password_hash="hash", is_active=True)):
            self.session.scalar.return_value = user
            with (
                patch.object(auth, "verify_password", return_value=False),
                patch.object(auth, "set_refresh_cookie") as cookie,
                self.assertRaises(HTTPException) as failure,
            ):
                await auth.login(
                    LoginRequest(username="ashik_590", password="incorrect"),
                    Response(), self.session,
                )
            self.assertEqual(failure.exception.status_code, 401)
            cookie.assert_not_called()

    async def test_language_pair_can_be_swapped_in_one_update(self):
        user = User(
            user_id=uuid4(), name="Md Azizul Hakim", username="ashik_590",
            email=None, is_active=True, native_language_id=1, target_language_id=2,
        )
        self.session.scalars.return_value = [self.native, self.target]
        updated = await users.update_practice_languages(
            PracticeLanguagesUpdate(native_language_code="en", target_language_code="bn"),
            user, self.session,
        )
        self.assertEqual(updated.native_language_id, 2)
        self.assertEqual(updated.target_language_id, 1)
        public = UserResponse.model_validate(updated)
        self.assertEqual(public.native_language.code, "en")
        self.assertEqual(public.target_language.code, "bn")
        self.assertIsNone(public.email)
        self.session.commit.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
