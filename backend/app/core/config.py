from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Language Practice API"
    api_v1_prefix: str = "/api/v1"
    frontend_origin: str = "http://localhost:5173"

    database_url: str

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    refresh_cookie_name: str = "habitus_refresh_token"
    refresh_cookie_secure: bool = False
    refresh_cookie_samesite: Literal["lax", "strict", "none"] = "lax"

    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"

    frontend_dist_dir: str | None = None
    profile_picture_storage: Literal["local", "supabase"] = "local"
    supabase_url: str | None = None
    supabase_service_role_key: str | None = None
    supabase_storage_bucket: str = "profile-pictures"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def refresh_cookie_max_age(self) -> int:
        return self.refresh_token_expire_days * 24 * 60 * 60


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
