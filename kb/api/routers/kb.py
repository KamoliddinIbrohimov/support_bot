from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from api.auth import get_project_id
from api.schemas import (
    KBEntryCreate,
    KBEntryRead,
    SearchRequest,
    SearchResponse,
    SearchResult,
    VerifyRequest,
)
from config.logger import logger
from database.connection import get_session
from database.repositories import KBRepository
from services.embedding_service import get_embedding, get_query_embedding

router = APIRouter(prefix="/kb", tags=["knowledge-base"])


@router.post("/search", response_model=SearchResponse)
async def search(
    payload: SearchRequest,
    project_id: str = Depends(get_project_id),
) -> SearchResponse:
    """Semantic similarity search — call this BEFORE any LLM completion."""
    embedding = await get_query_embedding(payload.query)
    if embedding is None:
        return SearchResponse(results=[], found=False)

    async with get_session() as session:
        repo = KBRepository(session)
        matches = await repo.similarity_search(
            embedding=embedding,
            project_id=project_id,
            threshold=payload.threshold,
            limit=payload.limit,
        )

        if matches:
            # Increment resolution count for best match
            best_id = matches[0][0].id
            await repo.increment_resolution(best_id)

    logger.info(
        f"KB search: project={project_id} query_len={len(payload.query)} "
        f"matches={len(matches)} threshold={payload.threshold}"
    )

    results = [
        SearchResult(entry=KBEntryRead.model_validate(entry), similarity=sim)
        for entry, sim in matches
    ]
    return SearchResponse(results=results, found=bool(results))


@router.post("/entries", response_model=KBEntryRead, status_code=status.HTTP_201_CREATED)
async def create_entry(
    payload: KBEntryCreate,
    project_id: str = Depends(get_project_id),
) -> KBEntryRead:
    """Create a new KB entry. Generates embedding automatically."""
    # Build text for embedding: combine title + description + solution
    embed_text = " ".join(filter(None, [payload.title, payload.description, payload.solution]))
    embedding = await get_embedding(embed_text)

    async with get_session() as session:
        repo = KBRepository(session)
        entry = await repo.create(
            project_id=project_id,
            title=payload.title,
            description=payload.description,
            solution=payload.solution,
            language=payload.language,
            embedding=embedding,
            source=payload.source,
            status=payload.status,
            is_shared=payload.is_shared,
        )
    return KBEntryRead.model_validate(entry)


@router.get("/entries", response_model=list[KBEntryRead])
async def list_entries(
    status_filter: str | None = None,
    limit: int = 50,
    project_id: str = Depends(get_project_id),
) -> list[KBEntryRead]:
    async with get_session() as session:
        repo = KBRepository(session)
        entries = await repo.list_by_project(
            project_id=project_id,
            status=status_filter,
            limit=min(limit, 200),
        )
    return [KBEntryRead.model_validate(e) for e in entries]


@router.get("/entries/{entry_id}", response_model=KBEntryRead)
async def get_entry(
    entry_id: UUID,
    project_id: str = Depends(get_project_id),
) -> KBEntryRead:
    async with get_session() as session:
        repo = KBRepository(session)
        entry = await repo.get(entry_id)
    if entry is None or entry.project_id != project_id:
        raise HTTPException(status_code=404, detail="Entry not found")
    return KBEntryRead.model_validate(entry)


@router.patch("/entries/{entry_id}/verify", response_model=KBEntryRead)
async def verify_entry(
    entry_id: UUID,
    payload: VerifyRequest,
    project_id: str = Depends(get_project_id),
) -> KBEntryRead:
    """Approve a pending entry — makes it eligible for auto-answering."""
    async with get_session() as session:
        repo = KBRepository(session)
        entry = await repo.get(entry_id)
        if entry is None or entry.project_id != project_id:
            raise HTTPException(status_code=404, detail="Entry not found")
        entry = await repo.verify(entry_id, payload.verified_by)
    logger.info(f"KB entry verified: {entry_id} by {payload.verified_by}")
    return KBEntryRead.model_validate(entry)


@router.patch("/entries/{entry_id}/reject", response_model=KBEntryRead)
async def reject_entry(
    entry_id: UUID,
    project_id: str = Depends(get_project_id),
) -> KBEntryRead:
    """Reject a pending entry."""
    async with get_session() as session:
        repo = KBRepository(session)
        entry = await repo.get(entry_id)
        if entry is None or entry.project_id != project_id:
            raise HTTPException(status_code=404, detail="Entry not found")
        entry = await repo.reject(entry_id)
    return KBEntryRead.model_validate(entry)
