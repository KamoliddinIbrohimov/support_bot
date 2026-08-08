from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Telegram
    BOT_TOKEN: str
    ADMINS_RAW: str = Field(
        default="",
        validation_alias=AliasChoices("ADMINS", "ADMIN_IDS"),
    )

    # Postgres
    POSTGRES_USER: str = "support_user"
    POSTGRES_PASSWORD: str = "support_pass"
    POSTGRES_DB: str = "support_bot"
    POSTGRES_HOST: str = Field(
        default="postgres",
        validation_alias=AliasChoices("POSTGRES_HOST", "ip", "IP"),
    )
    POSTGRES_PORT: int = 5432
    DATABASE_URL: str | None = None

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    # Conversation state TTL in seconds (how long to wait for screenshot after asking)
    CONV_STATE_TTL: int = 3600

    # OCR
    OCR_LANGUAGES_RAW: str = Field(
        default="ru,en",
        validation_alias=AliasChoices("OCR_LANGUAGES"),
    )
    OCR_USE_GPU: bool = False
    OCR_MIN_CONFIDENCE: float = 0.3

    # Matching
    FUZZY_MATCH_THRESHOLD: int = 70

    # Storage
    IMAGE_STORAGE_PATH: str = "storage/images"

    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/bot.log"

    # Knowledge Base service
    KB_API_URL: str = ""           # e.g. http://kb-api:8000
    KB_API_KEY: str = ""           # API key for this project
    KB_SIMILARITY_THRESHOLD: float = 0.90

    # Admin panel JWT
    JWT_SECRET: str = "change-me-in-production-use-long-random-string"

    # AI (Google Gemini — classifier + relevance + vision + OCR)
    GOOGLE_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""  # ixtiyoriy, Google bo'lsa ishlatilmaydi
    VISION_DAILY_LIMIT_PER_USER: int = 10

    # Product domain description used for relevance check (Step 3).
    # Keep it short — it's injected into a cached system prompt.
    PRODUCT_DOMAIN: str = (
        "This bot supports a POS terminal system: fiscal receipt printers, "
        "payment terminals, cash register software, and their network/connectivity issues."
    )

    @property
    def ADMIN_IDS(self) -> list[int]:
        raw = self.ADMINS_RAW.strip()
        if not raw:
            return []
        return [int(x.strip()) for x in raw.split(",") if x.strip()]

    @property
    def OCR_LANGUAGES(self) -> list[str]:
        raw = self.OCR_LANGUAGES_RAW.strip()
        if not raw:
            return ["ru", "en"]
        return [x.strip() for x in raw.split(",") if x.strip()]

    @property
    def async_database_url(self) -> str:
        if self.DATABASE_URL:
            if self.DATABASE_URL.startswith("postgresql://"):
                return self.DATABASE_URL.replace(
                    "postgresql://", "postgresql+asyncpg://", 1
                )
            return self.DATABASE_URL
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def sync_database_url(self) -> str:
        return self.async_database_url.replace(
            "postgresql+asyncpg://", "postgresql+psycopg2://", 1
        )

    @property
    def image_storage_dir(self) -> Path:
        path = BASE_DIR / self.IMAGE_STORAGE_PATH
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def log_file_path(self) -> Path:
        path = BASE_DIR / self.LOG_FILE
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def vision_enabled(self) -> bool:
        return bool(self.GOOGLE_API_KEY or self.ANTHROPIC_API_KEY)

    @property
    def llm_enabled(self) -> bool:
        return bool(self.GOOGLE_API_KEY or self.ANTHROPIC_API_KEY)

    @property
    def active_ai(self) -> str:
        """Qaysi AI ishlatilayotgani: 'google' | 'anthropic' | 'none'"""
        if self.GOOGLE_API_KEY:
            return "google"
        if self.ANTHROPIC_API_KEY:
            return "anthropic"
        return "none"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
