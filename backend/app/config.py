"""Application configuration via pydantic-settings."""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings validated at startup."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Required
    anthropic_api_key: str
    database_url: str
    redis_url: str = "redis://localhost:6379"
    secret_key: str = "default-dev-secret-key-change-in-production"

    # Application
    environment: str = "development"
    app_name: str = "AppCompiler"
    app_version: str = "1.0.0"
    debug: bool = False

    # LLM defaults
    default_model: str = "claude-sonnet-4-20250514"
    fast_model: str = "claude-haiku-3-5-20241022"
    max_retries: int = 3
    llm_timeout: int = 120

    # Pipeline
    max_repair_attempts: int = 2
    max_concurrent_jobs: int = 5

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
