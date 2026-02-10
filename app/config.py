from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    FIREBASE_PROJECT_ID: str = Field(..., description="Firebase project id")
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = Field(
        default=None, description="Path to service account JSON"
    )
    FIREBASE_SERVICE_ACCOUNT_JSON: Optional[str] = Field(
        default=None, description="Raw service account JSON string"
    )

    FIRESTORE_REELS_COLLECTION: str = Field(default="sources_reels")
    FIRESTORE_JOBS_COLLECTION: str = Field(default="source_jobs")

    REDIS_URL: str = Field(default="redis://redis:6379/0")
    WHISPER_URL: str = Field(default="http://whisper-lb:8000/transcribe")
    TMP_DIR: str = Field(default="/tmp")

    MAX_ATTEMPTS: int = Field(default=3)
    LEASE_SECONDS: int = Field(default=300)
    API_PORT: int = Field(default=8000)
    LOG_LEVEL: str = Field(default="INFO")

    REQUIRE_INTERNAL_CLAIM: bool = Field(default=False)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
