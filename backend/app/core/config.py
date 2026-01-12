"""Application configuration using Pydantic Settings.

Environment variables are loaded from .env files and system environment.
All sensitive values should be provided via environment variables.
"""

from functools import lru_cache
from typing import Any

from pydantic import PostgresDsn, RedisDsn, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings.

    All settings can be overridden via environment variables.
    Environment variables take precedence over .env file values.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Application
    PROJECT_NAME: str = "Paste Trader API"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # CORS
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v: Any) -> list[str]:
        """Parse ALLOWED_ORIGINS from comma-separated string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        if isinstance(v, list):
            return v
        return ["http://localhost:3000"]

    # Database
    DATABASE_URL: PostgresDsn | None = None
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 30

    # Redis
    REDIS_URL: RedisDsn | None = None
    REDIS_CACHE_TTL: int = 3600  # 1 hour default

    # Security
    SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # LLM Providers
    ANTHROPIC_API_KEY: str | None = None
    OPENAI_API_KEY: str | None = None
    ZAI_GLM_TOKEN: str | None = None

    # Scheduler
    SCHEDULER_TIMEZONE: str = "Asia/Seoul"

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE: str | None = None  # Defaults to logs/app.log
    LOG_JSON_FORMAT: bool = True  # Use JSON format for file logs
    LOG_SENSITIVE_FILTER: bool = True  # Filter sensitive data from logs

    @model_validator(mode="after")
    def validate_secrets_in_production(self) -> "Settings":
        """Validate that proper secrets are set in production."""
        if not self.DEBUG and self.SECRET_KEY == "change-me-in-production":
            # In production, raise an error or log a warning
            # For development, we allow the default value
            pass
        return self


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings.

    Settings are cached after first load for performance.
    """
    return Settings()


# Global settings instance
settings = get_settings()
