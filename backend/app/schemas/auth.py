import re

from pydantic import BaseModel, Field, field_validator


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=30)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("username", mode="before")
    @classmethod
    def normalize_username(cls, value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("Enter your username.")
        username = value.strip().lower()
        if re.fullmatch(r"[a-z][a-z0-9_]{2,29}", username) is None:
            raise ValueError("Enter a valid username using letters, numbers, or underscores.")
        return username


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
