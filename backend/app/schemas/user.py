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
        if len(normalized_name) < 2:
            raise ValueError("Name must contain at least two visible characters.")
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
    native_language: LanguagePublic


class NativeLanguageUpdate(BaseModel):
    native_language_code: str = Field(min_length=2, max_length=10)

    @field_validator("native_language_code")
    @classmethod
    def normalize_language_code(cls, value: str) -> str:
        return value.strip().lower()
