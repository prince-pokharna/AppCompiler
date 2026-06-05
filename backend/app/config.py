"""Application configuration via pydantic-settings."""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings validated at startup."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Required
    openai_api_key: str
    database_url: str = ""
    redis_url: str = "redis://localhost:6379"
    secret_key: str = "default-dev-secret-key-change-in-production"

    # Application
    environment: str = "development"
    app_name: str = "AppCompiler"
    app_version: str = "1.0.0"
    debug: bool = False

    # LLM Settings
    default_model: str = "gpt-4o"
    fast_model: str = "gpt-4o-mini"
    max_retries: int = 3
    llm_timeout: int = 60

    # Pipeline
    max_repair_attempts: int = 2
    max_concurrent_jobs: int = 5
    pipeline_timeout_seconds: int = 600
    pipeline_stage_timeout_seconds: int = 90

    # API auth (also reads API_SECRET_KEY env var in deps.py)
    api_secret_key: str | None = None

    # CORS
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance. Raises ValidationError if required env vars are missing."""
    return Settings()  # type: ignore[call-arg]
