"""In-memory cache of approved group IDs.

Loaded from DB at startup; updated instantly on approve/reject.
Avoids a DB query on every group message.
"""
from __future__ import annotations

_approved: set[int] = set()


async def load() -> None:
    from database.connection import get_session
    from database.repositories import GroupRepository
    async with get_session() as session:
        groups = await GroupRepository(session).list_approved()
        _approved.clear()
        _approved.update(g.chat_id for g in groups)


def is_approved(chat_id: int) -> bool:
    return chat_id in _approved


def mark_approved(chat_id: int) -> None:
    _approved.add(chat_id)


def mark_removed(chat_id: int) -> None:
    _approved.discard(chat_id)
