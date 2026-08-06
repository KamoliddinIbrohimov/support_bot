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

    POSTGRES_USER: str = "kb_user"
    POSTGRES_PASSWORD: str = "kb_pass"
    POSTGRES_DB: str = "kb"
    POSTGRES_HOST: str = Field(default="localhost", validation_alias=AliasChoices("POSTGRES_HOST", "ip"))
    POSTGRES_PORT: int = 5432
    DATABASE_URL: str | None = None

    GOOGLE_API_KEY: str = ""

    KB_SIMILARITY_THRESHOLD: float = 0.90
    KB_EMBEDDING_DIMS: int = 768

    # Ishga tushganda shu kalit va project_id avtomatik yaratiladi
    KB_SEED_API_KEY: str = ""
    KB_SEED_PROJECT_ID: str = "support_bot"

    LOG_LEVEL: str = "INFO"

    @property
    def async_database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def sync_database_url(self) -> str:
        return self.async_database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)

    @property
    def embedding_enabled(self) -> bool:
        return bool(self.GOOGLE_API_KEY)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
