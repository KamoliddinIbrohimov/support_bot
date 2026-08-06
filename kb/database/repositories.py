from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence
from uuid import UUID

from sqlalchemy import and_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import ApiKey, KBError


class ApiKeyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_project_id(self, key: str) -> str | None:
        row = await self._session.get(ApiKey, key)
        return row.project_id if row else None

    async def create(self, key: str, project_id: str, description: str | None = None) -> ApiKey:
        obj = ApiKey(key=key, project_id=project_id, description=description)
        self._session.add(obj)
        await self._session.flush()
        return obj


class KBRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        project_id: str,
        solution: str,
        title: str | None = None,
        description: str | None = None,
        language: str | None = None,
        embedding: list[float] | None = None,
        source: str = "manual",
        status: str = "pending",
        is_shared: bool = False,
    ) -> KBError:
        entry = KBError(
            project_id=project_id,
            title=title,
            description=description,
            solution=solution,
            language=language,
            embedding=embedding,
            source=source,
            status=status,
            is_shared=is_shared,
        )
        self._session.add(entry)
        await self._session.flush()
        return entry

    async def get(self, entry_id: UUID) -> KBError | None:
        return await self._session.get(KBError, entry_id)

    async def list_by_project(
        self,
        project_id: str,
        status: str | None = None,
        limit: int = 50,
    ) -> Sequence[KBError]:
        q = select(KBError).where(KBError.project_id == project_id)
        if status:
            q = q.where(KBError.status == status)
        q = q.order_by(KBError.created_at.desc()).limit(limit)
        result = await self._session.execute(q)
        return result.scalars().all()

    async def similarity_search(
        self,
        embedding: list[float],
        project_id: str,
        threshold: float = 0.90,
        limit: int = 3,
    ) -> list[tuple[KBError, float]]:
        """Cosine similarity search — returns (entry, similarity_score) pairs."""
        # Cosine distance with pgvector: <=> operator
        distance_col = KBError.embedding.cosine_distance(embedding).label("distance")

        result = await self._session.execute(
            select(KBError, distance_col)
            .where(
                and_(
                    KBError.status == "verified",
                    KBError.embedding.is_not(None),
                    or_(
                        KBError.project_id == project_id,
                        KBError.is_shared == True,
                    ),
                )
            )
            .order_by(distance_col)
            .limit(limit * 3)  # fetch more, filter by threshold in Python
        )

        rows = result.all()
        matches = []
        for row, distance in rows:
            similarity = 1.0 - float(distance)
            if similarity >= threshold:
                matches.append((row, similarity))

        return matches[:limit]

    async def verify(self, entry_id: UUID, verified_by: int) -> KBError | None:
        entry = await self.get(entry_id)
        if entry is None:
            return None
        entry.status = "verified"
        entry.verified_by = verified_by
        entry.verified_at = datetime.now(tz=timezone.utc)
        return entry

    async def reject(self, entry_id: UUID) -> KBError | None:
        entry = await self.get(entry_id)
        if entry is None:
            return None
        entry.status = "rejected"
        return entry

    async def increment_resolution(self, entry_id: UUID) -> None:
        await self._session.execute(
            update(KBError)
            .where(KBError.id == entry_id)
            .values(resolution_count=KBError.resolution_count + 1)
        )
