from functools import lru_cache
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "FWZ Energy & Electrical"
    environment: str = "development"
    base_url: str = "http://localhost:8000"

    # Default to SQLite for local dev; override with DATABASE_URL in prod.
    database_url: str = "sqlite+aiosqlite:///./dev.db"

    secret_key: str = "change-me"
    access_token_expire_minutes: int = 60 * 12
    reset_token_expire_minutes: int = 30
    reset_request_cooldown_seconds: int = 60
    rate_limit_window_seconds: int = 60
    rate_limit_max_requests: int = 120

    auto_create_db: bool = True

    db_connect_timeout_seconds: int | None = None
    db_connect_ssl: bool | None = None
    test_database_url: str | None = None

    # SMTP Configuration (Defaulting to Hostinger settings as a baseline)
    smtp_host: str = "smtp.hostinger.com"
    smtp_port: int = 587
    smtp_user: str | None = "info@fwz.sa"
    smtp_password: str | None = None
    smtp_from_email: str = "info@fwz.sa"
    smtp_tls: bool = True

    @model_validator(mode="after")
    def _check_production_secrets(self) -> "Settings":
        if self.environment == "production" and self.secret_key in ("change-me", ""):
            raise ValueError(
                "SECRET_KEY must be set to a secure random value in production. "
                "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
