import re
import unicodedata
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.schemas.catalog import LanguagePublic


class UserRegister(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    username: str = Field(min_length=3, max_length=30)
    email: EmailStr | None = None
    password: str = Field(min_length=8, max_length=128)
    native_language_code: str = Field(min_length=2, max_length=10)
    target_language_code: str = Field(min_length=2, max_length=10)

    @field_validator("username", mode="before")
    @classmethod
    def normalize_username(cls, value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("Enter a valid username.")
        username = value.strip().lower()
        if re.fullmatch(r"[a-z][a-z0-9_]{2,29}", username) is None:
            raise ValueError(
                "Username must be 3–30 characters, start with a letter, "
                "and contain only English letters, numbers, or underscores."
            )
        return username

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized_name = " ".join(value.split())
        allowed_punctuation = {" ", "'", "’", ".", "-"}
        letters = [
            character
            for character in normalized_name
            if unicodedata.category(character).startswith("L")
        ]
        has_invalid_character = any(
            not (
                unicodedata.category(character).startswith(("L", "M"))
                or character in allowed_punctuation
            )
            for character in normalized_name
        )
        if (
            len(letters) < 2
            or has_invalid_character
            or not unicodedata.category(normalized_name[0]).startswith("L")
            or not unicodedata.category(normalized_name[-1]).startswith(("L", "M"))
        ):
            raise ValueError(
                "Enter a valid name using letters, spaces, apostrophes, periods, "
                "or hyphens."
            )
        return normalized_name

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().lower() or None
        return value

    @field_validator("native_language_code", "target_language_code")
    @classmethod
    def normalize_language_code(cls, value: str) -> str:
        return value.strip().lower()

    @model_validator(mode="after")
    def require_different_languages(self) -> "UserRegister":
        if self.native_language_code == self.target_language_code:
            raise ValueError("Native and target languages must be different.")
        return self


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    name: str
    username: str
    email: EmailStr | None
    is_active: bool
    profile_picture_url: str | None
    native_language: LanguagePublic
    target_language: LanguagePublic


class NativeLanguageUpdate(BaseModel):
    native_language_code: str = Field(min_length=2, max_length=10)

    @field_validator("native_language_code")
    @classmethod
    def normalize_language_code(cls, value: str) -> str:
        return value.strip().lower()


class PracticeLanguagesUpdate(BaseModel):
    native_language_code: str = Field(min_length=2, max_length=10)
    target_language_code: str = Field(min_length=2, max_length=10)

    @field_validator("native_language_code", "target_language_code")
    @classmethod
    def normalize_language_code(cls, value: str) -> str:
        return value.strip().lower()

    @model_validator(mode="after")
    def require_different_languages(self) -> "PracticeLanguagesUpdate":
        if self.native_language_code == self.target_language_code:
            raise ValueError("Native and target languages must be different.")
        return self
