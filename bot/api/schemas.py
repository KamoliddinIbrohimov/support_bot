from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ErrorCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    keywords: list[str] = Field(..., min_length=1)
    description: str | None = None
    solution: str = Field(..., min_length=5)
    # Optional bilingual fields
    title_ru: str | None = None
    title_uz: str | None = None
    keywords_ru: list[str] | None = None
    keywords_uz: list[str] | None = None
    description_ru: str | None = None
    description_uz: str | None = None
    solution_ru: str | None = None
    solution_uz: str | None = None
    solution_video_file_id: str | None = None


class ErrorRead(BaseModel):
    id: int
    title: str
    keywords: list[str]
    description: str | None
    solution: str
    title_ru: str | None
    title_uz: str | None
    keywords_ru: list[str] | None
    keywords_uz: list[str] | None
    description_ru: str | None
    description_uz: str | None
    solution_ru: str | None
    solution_uz: str | None
    solution_video_file_id: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class OCRLogRead(BaseModel):
    id: int
    telegram_user: int
    telegram_username: str | None
    chat_id: int
    image_path: str
    detected_text: str | None
    confidence: float | None
    matched_error_id: int | None
    match_score: float | None
    matched_via: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class HealthResponse(BaseModel):
    status: str = "ok"
