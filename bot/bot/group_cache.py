"""In-memory cache of approved group IDs, modes and user roles.

Loaded from DB at startup; updated instantly on approve/reject/mode-change.
"""
from __future__ import annotations

_approved: set[int] = set()


async def load() -> None:
    from bot import role_cache
    from database.connection import get_session
    from database.repositories import GroupRepository, GroupUserRoleRepository
    async with get_session() as session:
        groups = await GroupRepository(session).list_approved()
        _approved.clear()
        _approved.update(g.chat_id for g in groups)
        for g in groups:
            role_cache.set_mode(g.chat_id, g.bot_mode)
            roles = await GroupUserRoleRepository(session).list_by_group(g.chat_id)
            role_cache.load_roles(g.chat_id, roles)


def is_approved(chat_id: int) -> bool:
    return chat_id in _approved


def mark_approved(chat_id: int) -> None:
    _approved.add(chat_id)


def mark_removed(chat_id: int) -> None:
    _approved.discard(chat_id)
