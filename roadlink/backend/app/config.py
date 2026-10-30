"""Application configuration via pydantic-settings."""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    ENV: Literal["development", "test", "production"] = "development"
    APP_NAME: str = "RoadLink"
    APP_VERSION: str = "0.1.0"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./roadlink.db"
    TEST_DATABASE_URL: str = "sqlite+aiosqlite:///:memory:"

    # JWT
    JWT_SECRET: str = "CHANGE_ME_IN_PRODUCTION_MUST_BE_32_CHARS_MIN"
    ACCESS_TOKEN_TTL_S: int = 900        # 15 min
    REFRESH_TOKEN_TTL_S: int = 2_592_000  # 30 days

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    # Storage
    STORAGE_BACKEND: Literal["local", "s3"] = "local"
    UPLOAD_DIR: str = "./uploads"
    MAX_IMAGE_BYTES: int = 5_242_880  # 5 MB

    # Location
    LOCATION_MIN_INTERVAL_S: int = 5
    LOCATION_MAX_ACCURACY_M: float = 1000.0
    LOCATION_RETENTION_HOURS: int = 24
    ACTIVE_WINDOW_S: int = 120
    SOS_LOCATION_MAX_AGE_S: int = 1800

    # Radius options (comma-separated metres)
    RADIUS_OPTIONS_M: str = "5000,10000,25000,50000,100000"

    @property
    def radius_options_list(self) -> list[int]:
        return [int(x.strip()) for x in self.RADIUS_OPTIONS_M.split(",")]

    # SOS stages
    SOS_RADIUS_STAGES_M: str = "5000,15000,30000,50000,100000"
    SOS_STAGE_DELAYS_S: str = "0,180,300,420,600"
    SOS_CRITICAL_DELAY_FACTOR: float = 0.5
    SOS_OPEN_TTL_S: int = 10_800    # 3 h
    SOS_ACTIVE_TTL_S: int = 43_200  # 12 h
    SOS_MAX_ACTIVE_PER_USER: int = 3
    SOS_COOLDOWN_S: int = 120

    @property
    def sos_stages_list(self) -> list[int]:
        return [int(x.strip()) for x in self.SOS_RADIUS_STAGES_M.split(",")]

    @property
    def sos_delays_list(self) -> list[int]:
        return [int(x.strip()) for x in self.SOS_STAGE_DELAYS_S.split(",")]

    # Community
    COMMUNITY_MESSAGE_TTL_S: int = 7200

    # Chat
    CHAT_RETENTION_DAYS: int = 30
    CONVERSATION_CLOSE_GRACE_S: int = 86400

    # Safety
    REPORT_RESTRICT_THRESHOLD: int = 5
    EMERGENCY_NUMBER: str = "112"

    # AI
    AI_PROVIDER: Literal["ollama", "none"] = "none"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "gemma3:1b"
    AI_TIMEOUT_S: float = 8.0
    AI_MAX_INPUT_CHARS: int = 1000

    # Web Push (VAPID)
    VAPID_PUBLIC_KEY: str = ""
    VAPID_PRIVATE_KEY: str = ""
    VAPID_SUBJECT: str = "mailto:roadlink@example.com"

    # Overpass / Places
    OVERPASS_URLS: str = "https://overpass-api.de/api/interpreter,https://overpass.kumi.systems/api/interpreter"
    PLACES_CACHE_TTL_S: int = 600

    @property
    def overpass_urls_list(self) -> list[str]:
        return [u.strip() for u in self.OVERPASS_URLS.split(",") if u.strip()]

    @model_validator(mode="after")
    def check_production_secrets(self) -> "Settings":
        if self.ENV == "production":
            if self.JWT_SECRET == "CHANGE_ME_IN_PRODUCTION_MUST_BE_32_CHARS_MIN":
                raise ValueError("JWT_SECRET must be set in production")
        if len(self.JWT_SECRET) < 32:
            raise ValueError("JWT_SECRET must be at least 32 characters")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
