from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    env: str = "development"
    secret_key: str = "hard-to-guess-string-change-in-production"
    database_url: str = "sqlite+aiosqlite:///./tmp/dev.db"
    yandex_verification: str | None = None
    yandex_metrika: str = "76938046"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
