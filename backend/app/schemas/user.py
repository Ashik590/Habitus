import unicodedata
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.schemas.catalog import LanguagePublic


class UserRegister(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    native_language_code: str = Field(min_length=2, max_length=10)

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

    @field_validator("email", mode="after")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).lower()

    @field_validator("native_language_code")
    @classmethod
    def normalize_language_code(cls, value: str) -> str:
        return value.strip().lower()


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    name: str
    email: EmailStr
    is_active: bool
    profile_picture_url: str | None
    native_language: LanguagePublic


class NativeLanguageUpdate(BaseModel):
    native_language_code: str = Field(min_length=2, max_length=10)

    @field_validator("native_language_code")
    @classmethod
    def normalize_language_code(cls, value: str) -> str:
        return value.strip().lower()
