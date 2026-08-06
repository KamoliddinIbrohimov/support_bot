from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class KBEntryCreate(BaseModel):
    title: str | None = None
    description: str | None = None
    solution: str = Field(..., min_length=3)
    language: str | None = None
    source: str = "manual"
    is_shared: bool = False
    status: str = "pending"


class KBEntryRead(BaseModel):
    id: UUID
    project_id: str
    is_shared: bool
    title: str | None
    description: str | None
    solution: str
    language: str | None
    source: str
    status: str
    resolution_count: int
    created_at: datetime
    verified_by: int | None
    verified_at: datetime | None

    model_config = {"from_attributes": True}


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    threshold: float = Field(default=0.90, ge=0.0, le=1.0)
    limit: int = Field(default=3, ge=1, le=10)


class SearchResult(BaseModel):
    entry: KBEntryRead
    similarity: float


class SearchResponse(BaseModel):
    results: list[SearchResult]
    found: bool


class VerifyRequest(BaseModel):
    verified_by: int  # telegram_id of admin


class HealthResponse(BaseModel):
    status: str = "ok"
    embedding_enabled: bool
