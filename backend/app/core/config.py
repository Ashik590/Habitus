from functools import lru_cache

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

    gemini_api_key: str | None = None
    gemini_api_key_2: str | None = None
    gemini_api_key_3: str | None = None
    gemini_api_keys: str | None = None
    gemini_model: str = "gemini-2.5-flash"

    whisper_model: str = "tiny"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def all_gemini_api_keys(self) -> list[str]:
        keys: list[str] = []
        if self.gemini_api_keys:
            keys.extend(k.strip() for k in self.gemini_api_keys.split(",") if k.strip())
        for key in (self.gemini_api_key, self.gemini_api_key_2, self.gemini_api_key_3):
            if key and key.strip() and key.strip() not in keys:
                keys.append(key.strip())
        return keys


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
