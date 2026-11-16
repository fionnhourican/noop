"""Application configuration loaded from environment variables."""

import os
from typing import List
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """NOOP Home Lab API settings."""
    PROJECT_NAME: str = "NOOP Home Lab API"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = "production"

    # PostgreSQL configuration
    POSTGRES_SERVER: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "noop"
    POSTGRES_PASSWORD: str = "changeme_postgres_password"
    POSTGRES_DB: str = "noop_homelab"

    # Separate credentials
    INGESTION_TOKEN: SecretStr = SecretStr("changeme_ingestion_bearer_token_min_32_chars")
    DASHBOARD_TOKEN: SecretStr = SecretStr("changeme_dashboard_session_token")

    # Allowed CORS origins
    CORS_ORIGINS: List[str] = [
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def async_database_url(self) -> str:
        """Asynchronous database URL for SQLAlchemy asyncpg."""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def sync_database_url(self) -> str:
        """Synchronous database URL for Alembic migrations."""
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


settings = Settings()
