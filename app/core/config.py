from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "ANHA Trading"
    environment: str = "development"

    # Default to SQLite for local dev; override with DATABASE_URL in prod.
    database_url: str = "sqlite+aiosqlite:///./dev.db"

    secret_key: str = "change-me"
    access_token_expire_minutes: int = 60 * 12
    reset_token_expire_minutes: int = 30

    auto_create_db: bool = True

    db_connect_timeout_seconds: int | None = None
    db_connect_ssl: bool | None = None
    test_database_url: str | None = None



@lru_cache
def get_settings() -> Settings:
    return Settings()
