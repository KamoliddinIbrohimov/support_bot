"""Admin: group management — list, approve/reject, mode, settings, roles, learning feed."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import cast, Date, func, or_, select, and_

from api.admin.deps import get_current_admin
from database.connection import get_session
from database.repositories import GroupRepository
from database.models import (
    ApprovedGroup, GroupUserRole, LearningFeedEntry,
    MessageClassification, OCRLog, ErrorEntry,
)

router = APIRouter(prefix="/admin/groups", tags=["admin-groups"])

# ── Schemas ────────────────────────────────────────────────────────────────────

class GroupAdminRead(BaseModel):
    chat_id: int
    title: str | None
    username: str | None
    chat_type: str | None
    added_by_id: int | None
    added_by_name: str | None
    added_by_username: str | None
    status: str
    bot_mode: str
    poster_auto_answer: bool
    approved_by: int | None
    created_at: str
    updated_at: str
    model_config = {"from_attributes": True}


class ModeUpdate(BaseModel):
    mode: str  # learning | knowledge | express


class SettingsUpdate(BaseModel):
    poster_auto_answer: bool


class RoleUpdate(BaseModel):
    role: str  # poster_staff | plugin_staff | customer
    is_manual_override: bool = True


class UserRoleRead(BaseModel):
    id: int
    group_id: int
    telegram_user_id: int
    username: str | None
    full_name: str | None
    role: str
    confidence_score: float
    is_manual_override: bool
    updated_at: str


class LearningEntryRead(BaseModel):
    id: int
    group_id: int
    question_text: str | None
    answer_text: str | None
    question_user_id: int | None
    answer_user_id: int | None
    question_username: str | None
    answer_username: str | None
    is_confirmed: bool
    created_at: str


class TopErrorItem(BaseModel):
    error_id: int | None
    title: str
    count: int


class GroupTimelinePoint(BaseModel):
    date: str
    questions: int


class GroupDetailStats(BaseModel):
    chat_id: int
    title: str | None
    status: str
    bot_mode: str
    poster_auto_answer: bool
    total_questions: int
    resolved_by_ai: int
    resolved_by_support: int
    unresolved: int
    resolution_rate: float
    top_errors: list[TopErrorItem]
    timeline: list[GroupTimelinePoint]


# ── Helper ─────────────────────────────────────────────────────────────────────

def _to_read(g: ApprovedGroup) -> GroupAdminRead:
    return GroupAdminRead(
        chat_id=g.chat_id, title=g.title, username=g.username,
        chat_type=g.chat_type, added_by_id=g.added_by_id,
        added_by_name=g.added_by_name, added_by_username=g.added_by_username,
        status=g.status, bot_mode=g.bot_mode, poster_auto_answer=g.poster_auto_answer,
        approved_by=g.approved_by,
        created_at=g.created_at.isoformat(), updated_at=g.updated_at.isoformat(),
    )


# ── List ───────────────────────────────────────────────────────────────────────

@router.get("", response_model=list[GroupAdminRead])
async def list_groups(
    status_filter: str | None = Query(None),
    search: str | None = Query(None),
    _admin: int = Depends(get_current_admin),
):
    async with get_session() as session:
        stmt = select(ApprovedGroup).order_by(ApprovedGroup.created_at.desc())
        if status_filter in ("pending", "approved", "rejected"):
            stmt = stmt.where(ApprovedGroup.status == status_filter)
        if search:
            like = f"%{search}%"
            stmt = stmt.where(
                or_(ApprovedGroup.title.ilike(like), ApprovedGroup.username.ilike(like))
            )
        result = await session.execute(stmt)
        groups = list(result.scalars().all())
    return [_to_read(g) for g in groups]


# ── Approve / Reject ───────────────────────────────────────────────────────────

@router.post("/{chat_id}/approve", response_model=GroupAdminRead)
async def approve_group(chat_id: int, admin_id: int = Depends(get_current_admin)):
    async with get_session() as session:
        group = await GroupRepository(session).approve(chat_id, admin_id)
    if group is None:
        raise HTTPException(status_code=404, detail="Guruh topilmadi")
    try:
        from bot import group_cache, role_cache
        group_cache.mark_approved(chat_id)
        role_cache.set_mode(chat_id, group.bot_mode)
    except Exception:
        pass
    return _to_read(group)


@router.post("/{chat_id}/reject", response_model=GroupAdminRead)
async def reject_group(chat_id: int, admin_id: int = Depends(get_current_admin)):
    async with get_session() as session:
        group = await GroupRepository(session).reject(chat_id, admin_id)
    if group is None:
        raise HTTPException(status_code=404, detail="Guruh topilmadi")
    try:
        from bot import group_cache, role_cache
        group_cache.mark_removed(chat_id)
        role_cache.remove_mode(chat_id)
    except Exception:
        pass
    return _to_read(group)


# ── Mode & Settings ────────────────────────────────────────────────────────────

@router.patch("/{chat_id}/mode")
async def update_mode(
    chat_id: int, body: ModeUpdate, _admin: int = Depends(get_current_admin),
):
    if body.mode not in ("learning", "knowledge", "express"):
        raise HTTPException(400, "Yaroqsiz rejim. Ruxsat etilganlar: learning, knowledge, express")
    async with get_session() as session:
        group = await session.get(ApprovedGroup, chat_id)
        if group is None:
            raise HTTPException(404, "Guruh topilmadi")
        group.bot_mode = body.mode
        await session.flush()
    try:
        from bot import role_cache
        role_cache.set_mode(chat_id, body.mode)
    except Exception:
        pass
    return {"chat_id": chat_id, "bot_mode": body.mode}


@router.patch("/{chat_id}/settings")
async def update_settings(
    chat_id: int, body: SettingsUpdate, _admin: int = Depends(get_current_admin),
):
    async with get_session() as session:
        group = await session.get(ApprovedGroup, chat_id)
        if group is None:
            raise HTTPException(404, "Guruh topilmadi")
        group.poster_auto_answer = body.poster_auto_answer
        await session.flush()
    return {"chat_id": chat_id, "poster_auto_answer": body.poster_auto_answer}


# ── Roles ──────────────────────────────────────────────────────────────────────

@router.get("/{chat_id}/roles", response_model=list[UserRoleRead])
async def list_roles(chat_id: int, _admin: int = Depends(get_current_admin)):
    async with get_session() as session:
        result = await session.execute(
            select(GroupUserRole).where(GroupUserRole.group_id == chat_id)
        )
        roles = result.scalars().all()
    return [
        UserRoleRead(
            id=r.id, group_id=r.group_id, telegram_user_id=r.telegram_user_id,
            username=r.username, full_name=r.full_name, role=r.role,
            confidence_score=r.confidence_score, is_manual_override=r.is_manual_override,
            updated_at=r.updated_at.isoformat(),
        )
        for r in roles
    ]


@router.patch("/{chat_id}/roles/{user_id}", response_model=UserRoleRead)
async def update_user_role(
    chat_id: int, user_id: int, body: RoleUpdate,
    _admin: int = Depends(get_current_admin),
):
    if body.role not in ("poster_staff", "plugin_staff", "communicator", "customer"):
        raise HTTPException(400, "Yaroqsiz rol")
    async with get_session() as session:
        result = await session.execute(
            select(GroupUserRole).where(
                and_(GroupUserRole.group_id == chat_id, GroupUserRole.telegram_user_id == user_id)
            )
        )
        role_obj = result.scalar_one_or_none()
        if role_obj is None:
            raise HTTPException(404, "Foydalanuvchi topilmadi")
        role_obj.role = body.role
        role_obj.is_manual_override = body.is_manual_override
        role_obj.updated_at = datetime.now(timezone.utc)
        await session.flush()
    return UserRoleRead(
        id=role_obj.id, group_id=role_obj.group_id,
        telegram_user_id=role_obj.telegram_user_id,
        username=role_obj.username, full_name=role_obj.full_name,
        role=role_obj.role, confidence_score=role_obj.confidence_score,
        is_manual_override=role_obj.is_manual_override,
        updated_at=role_obj.updated_at.isoformat(),
    )


# ── Learning Feed ──────────────────────────────────────────────────────────────

@router.get("/{chat_id}/learning-feed", response_model=list[LearningEntryRead])
async def get_learning_feed(
    chat_id: int, _admin: int = Depends(get_current_admin),
):
    async with get_session() as session:
        result = await session.execute(
            select(LearningFeedEntry)
            .where(LearningFeedEntry.group_id == chat_id)
            .order_by(LearningFeedEntry.created_at.desc())
            .limit(50)
        )
        entries = result.scalars().all()
    return [
        LearningEntryRead(
            id=e.id, group_id=e.group_id,
            question_text=e.question_text, answer_text=e.answer_text,
            question_user_id=e.question_user_id, answer_user_id=e.answer_user_id,
            question_username=e.question_username, answer_username=e.answer_username,
            is_confirmed=e.is_confirmed, created_at=e.created_at.isoformat(),
        )
        for e in entries
    ]


@router.post("/{chat_id}/learning-feed/{entry_id}/confirm")
async def confirm_learning_entry(
    chat_id: int, entry_id: int, _admin: int = Depends(get_current_admin),
):
    async with get_session() as session:
        entry = await session.get(LearningFeedEntry, entry_id)
        if entry is None or entry.group_id != chat_id:
            raise HTTPException(404, "Yozuv topilmadi")
        entry.is_confirmed = True
        await session.flush()
    return {"id": entry_id, "is_confirmed": True}


# ── Per-group Stats ────────────────────────────────────────────────────────────

@router.get("/{chat_id}/stats", response_model=GroupDetailStats)
async def group_detail_stats(
    chat_id: int,
    days: int = Query(30, ge=7, le=365),
    _admin: int = Depends(get_current_admin),
):
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=days)

    async with get_session() as session:
        group = await session.get(ApprovedGroup, chat_id)
        if group is None:
            raise HTTPException(404, "Guruh topilmadi")

        total_q = await session.scalar(
            select(func.count()).where(
                and_(MessageClassification.chat_id == chat_id, MessageClassification.is_help_request == True)
            )
        ) or 0

        ai_resolved = await session.scalar(
            select(func.count()).where(
                and_(OCRLog.chat_id == chat_id, OCRLog.matched_error_id != None)
            )
        ) or 0

        from database.models import Conversation
        support_resolved = await session.scalar(
            select(func.count()).where(
                and_(Conversation.group_id == chat_id, Conversation.resolved_by == "support")
            )
        ) or 0

        rows = await session.execute(
            select(OCRLog.matched_error_id, ErrorEntry.title_ru, func.count().label("cnt"))
            .join(ErrorEntry, OCRLog.matched_error_id == ErrorEntry.id, isouter=True)
            .where(and_(OCRLog.chat_id == chat_id, OCRLog.matched_error_id != None))
            .group_by(OCRLog.matched_error_id, ErrorEntry.title_ru)
            .order_by(func.count().desc())
            .limit(5)
        )
        top_errors = [
            TopErrorItem(error_id=r.matched_error_id, title=r.title_ru or "—", count=r.cnt)
            for r in rows
        ]

        day_rows = await session.execute(
            select(cast(MessageClassification.created_at, Date).label("day"), func.count().label("cnt"))
            .where(
                and_(
                    MessageClassification.chat_id == chat_id,
                    MessageClassification.is_help_request == True,
                    MessageClassification.created_at >= since,
                )
            )
            .group_by("day").order_by("day")
        )
        daily_map = {str(r.day): r.cnt for r in day_rows}
        timeline = [
            GroupTimelinePoint(
                date=str((now - timedelta(days=days - 1 - i)).date()),
                questions=daily_map.get(str((now - timedelta(days=days - 1 - i)).date()), 0),
            )
            for i in range(days)
        ]

    unresolved = max(0, total_q - ai_resolved - support_resolved)
    rate = round((ai_resolved + support_resolved) / total_q * 100, 1) if total_q else 0.0

    return GroupDetailStats(
        chat_id=chat_id, title=group.title, status=group.status,
        bot_mode=group.bot_mode, poster_auto_answer=group.poster_auto_answer,
        total_questions=total_q, resolved_by_ai=ai_resolved,
        resolved_by_support=support_resolved, unresolved=unresolved,
        resolution_rate=rate, top_errors=top_errors, timeline=timeline,
    )
