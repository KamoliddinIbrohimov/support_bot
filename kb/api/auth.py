from __future__ import annotations

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from database.connection import get_session
from database.repositories import ApiKeyRepository

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)


async def get_project_id(api_key: str = Security(_api_key_header)) -> str:
    """Validate API key and return project_id."""
    async with get_session() as session:
        repo = ApiKeyRepository(session)
        project_id = await repo.get_project_id(api_key)

    if project_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    return project_id
