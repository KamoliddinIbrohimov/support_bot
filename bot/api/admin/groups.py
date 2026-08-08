"""Admin: group management — list, approve, reject."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from api.admin.deps import get_current_admin
from database.connection import get_session
from database.repositories import GroupRepository

router = APIRouter(prefix="/admin/groups", tags=["admin-groups"])


class GroupAdminRead(BaseModel):
    chat_id: int
    title: str | None
    username: str | None
    chat_type: str | None
    added_by_id: int | None
    added_by_name: str | None
    added_by_username: str | None
    status: str
    approved_by: int | None
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


@router.get("", response_model=list[GroupAdminRead])
async def list_groups(
    status_filter: str | None = Query(None, description="pending | approved | rejected"),
    _admin: int = Depends(get_current_admin),
):
    async with get_session() as session:
        repo = GroupRepository(session)
        if status_filter == "pending":
            groups = list(await repo.list_pending())
        elif status_filter == "approved":
            groups = list(await repo.list_approved())
        else:
            from sqlalchemy import select
            from database.models import ApprovedGroup
            result = await session.execute(
                select(ApprovedGroup).order_by(ApprovedGroup.created_at.desc())
            )
            groups = list(result.scalars().all())

    return [
        GroupAdminRead(
            chat_id=g.chat_id,
            title=g.title,
            username=g.username,
            chat_type=g.chat_type,
            added_by_id=g.added_by_id,
            added_by_name=g.added_by_name,
            added_by_username=g.added_by_username,
            status=g.status,
            approved_by=g.approved_by,
            created_at=g.created_at.isoformat(),
            updated_at=g.updated_at.isoformat(),
        )
        for g in groups
    ]


@router.post("/{chat_id}/approve", response_model=GroupAdminRead)
async def approve_group(
    chat_id: int,
    admin_id: int = Depends(get_current_admin),
):
    async with get_session() as session:
        group = await GroupRepository(session).approve(chat_id, admin_id)
    if group is None:
        raise HTTPException(status_code=404, detail="Guruh topilmadi")

    from bot import group_cache, role_cache
    group_cache.mark_approved(chat_id)
    role_cache.set_active(chat_id)

    return GroupAdminRead(
        chat_id=group.chat_id, title=group.title, username=group.username,
        chat_type=group.chat_type, added_by_id=group.added_by_id,
        added_by_name=group.added_by_name, added_by_username=group.added_by_username,
        status=group.status, approved_by=group.approved_by,
        created_at=group.created_at.isoformat(), updated_at=group.updated_at.isoformat(),
    )


@router.post("/{chat_id}/reject", response_model=GroupAdminRead)
async def reject_group(
    chat_id: int,
    admin_id: int = Depends(get_current_admin),
):
    async with get_session() as session:
        group = await GroupRepository(session).reject(chat_id, admin_id)
    if group is None:
        raise HTTPException(status_code=404, detail="Guruh topilmadi")

    try:
        from bot import group_cache, role_cache
        group_cache.mark_removed(chat_id)
        role_cache._group_mode.pop(chat_id, None)
    except Exception:
        pass

    return GroupAdminRead(
        chat_id=group.chat_id, title=group.title, username=group.username,
        chat_type=group.chat_type, added_by_id=group.added_by_id,
        added_by_name=group.added_by_name, added_by_username=group.added_by_username,
        status=group.status, approved_by=group.approved_by,
        created_at=group.created_at.isoformat(), updated_at=group.updated_at.isoformat(),
    )
