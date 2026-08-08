"""Admin: full CRUD for errors table with search + pagination."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from api.admin.deps import get_current_admin
from database.connection import get_session
from database.repositories import ErrorRepository

router = APIRouter(prefix="/admin/errors", tags=["admin-errors"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class ErrorAdminCreate(BaseModel):
    title_ru: str = Field(..., min_length=2, max_length=255)
    title_uz: str = Field(..., min_length=2, max_length=255)
    keywords_ru: list[str] = Field(..., min_length=1)
    keywords_uz: list[str] = Field(..., min_length=1)
    solution_ru: str = Field(..., min_length=5)
    solution_uz: str = Field(..., min_length=5)
    solution_video_file_id: str | None = None
    solution_image_file_id: str | None = None


class ErrorAdminUpdate(BaseModel):
    title_ru: str | None = None
    title_uz: str | None = None
    keywords_ru: list[str] | None = None
    keywords_uz: list[str] | None = None
    solution_ru: str | None = None
    solution_uz: str | None = None
    solution_video_file_id: str | None = None
    solution_image_file_id: str | None = None


class ErrorAdminRead(BaseModel):
    id: int
    title_ru: str | None
    title_uz: str | None
    keywords_ru: list[str] | None
    keywords_uz: list[str] | None
    solution_ru: str | None
    solution_uz: str | None
    solution_video_file_id: str | None
    solution_image_file_id: str | None
    created_at: str

    model_config = {"from_attributes": True}


class PaginatedErrors(BaseModel):
    items: list[ErrorAdminRead]
    total: int
    page: int
    page_size: int


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("", response_model=PaginatedErrors)
async def list_errors(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
    _admin: int = Depends(get_current_admin),
):
    async with get_session() as session:
        all_errors = list(await ErrorRepository(session).list_all())

    if search:
        q = search.lower()
        all_errors = [
            e for e in all_errors
            if q in (e.title_ru or "").lower()
            or q in (e.title_uz or "").lower()
            or any(q in kw.lower() for kw in (e.keywords_ru or []))
        ]

    total = len(all_errors)
    start = (page - 1) * page_size
    items = all_errors[start: start + page_size]

    return PaginatedErrors(
        items=[
            ErrorAdminRead(
                id=e.id,
                title_ru=e.title_ru,
                title_uz=e.title_uz,
                keywords_ru=e.keywords_ru,
                keywords_uz=e.keywords_uz,
                solution_ru=e.solution_ru,
                solution_uz=e.solution_uz,
                solution_video_file_id=e.solution_video_file_id,
                solution_image_file_id=e.solution_image_file_id,
                created_at=e.created_at.isoformat(),
            )
            for e in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=ErrorAdminRead, status_code=status.HTTP_201_CREATED)
async def create_error(
    payload: ErrorAdminCreate,
    _admin: int = Depends(get_current_admin),
):
    async with get_session() as session:
        entry = await ErrorRepository(session).create(
            title=payload.title_ru,
            keywords=payload.keywords_ru,
            solution=payload.solution_ru,
            title_ru=payload.title_ru,
            title_uz=payload.title_uz,
            keywords_ru=payload.keywords_ru,
            keywords_uz=payload.keywords_uz,
            solution_ru=payload.solution_ru,
            solution_uz=payload.solution_uz,
            solution_video_file_id=payload.solution_video_file_id,
            solution_image_file_id=payload.solution_image_file_id,
        )
        return ErrorAdminRead(
            id=entry.id,
            title_ru=entry.title_ru,
            title_uz=entry.title_uz,
            keywords_ru=entry.keywords_ru,
            keywords_uz=entry.keywords_uz,
            solution_ru=entry.solution_ru,
            solution_uz=entry.solution_uz,
            solution_video_file_id=entry.solution_video_file_id,
            solution_image_file_id=entry.solution_image_file_id,
            created_at=entry.created_at.isoformat(),
        )


@router.put("/{error_id}", response_model=ErrorAdminRead)
async def update_error(
    error_id: int,
    payload: ErrorAdminUpdate,
    _admin: int = Depends(get_current_admin),
):
    async with get_session() as session:
        repo = ErrorRepository(session)
        entry = await repo.get_by_id(error_id)
        if entry is None:
            raise HTTPException(status_code=404, detail="Topilmadi")
        if payload.title_ru is not None:
            entry.title = payload.title_ru
            entry.title_ru = payload.title_ru
        if payload.title_uz is not None:
            entry.title_uz = payload.title_uz
        if payload.keywords_ru is not None:
            entry.keywords = payload.keywords_ru
            entry.keywords_ru = payload.keywords_ru
        if payload.keywords_uz is not None:
            entry.keywords_uz = payload.keywords_uz
        if payload.solution_ru is not None:
            entry.solution = payload.solution_ru
            entry.solution_ru = payload.solution_ru
        if payload.solution_uz is not None:
            entry.solution_uz = payload.solution_uz
        if payload.solution_video_file_id is not None:
            entry.solution_video_file_id = payload.solution_video_file_id
        if payload.solution_image_file_id is not None:
            entry.solution_image_file_id = payload.solution_image_file_id
        await session.flush()
        return ErrorAdminRead(
            id=entry.id,
            title_ru=entry.title_ru,
            title_uz=entry.title_uz,
            keywords_ru=entry.keywords_ru,
            keywords_uz=entry.keywords_uz,
            solution_ru=entry.solution_ru,
            solution_uz=entry.solution_uz,
            solution_video_file_id=entry.solution_video_file_id,
            solution_image_file_id=entry.solution_image_file_id,
            created_at=entry.created_at.isoformat(),
        )


@router.delete("/{error_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_error(
    error_id: int,
    _admin: int = Depends(get_current_admin),
):
    async with get_session() as session:
        deleted = await ErrorRepository(session).delete(error_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Topilmadi")
