"""Admin: statistics endpoints."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select, and_

from api.admin.deps import get_current_admin
from database.connection import get_session
from database.models import ApprovedGroup, MessageClassification, OCRLog

router = APIRouter(prefix="/admin/stats", tags=["admin-stats"])


class OverviewStats(BaseModel):
    today_questions: int
    total_groups: int
    approved_groups: int
    total_errors_in_db: int
    resolution_rate_percent: float
    avg_response_time_sec: float | None


class DailyPoint(BaseModel):
    date: str
    questions: int
    resolved: int


class TopError(BaseModel):
    error_id: int | None
    title: str
    count: int


class GroupStat(BaseModel):
    chat_id: int
    title: str | None
    questions: int
    resolved_by_ai: int
    resolved_by_support: int


@router.get("/overview", response_model=OverviewStats)
async def overview(_admin: int = Depends(get_current_admin)):
    now = datetime.now(timezone.utc)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)

    async with get_session() as session:
        # Today's help requests
        today_q = await session.scalar(
            select(func.count()).where(
                and_(
                    MessageClassification.created_at >= today,
                    MessageClassification.is_help_request == True,
                )
            )
        )

        # Total & approved groups
        total_groups = await session.scalar(select(func.count()).select_from(ApprovedGroup))
        approved_groups = await session.scalar(
            select(func.count()).where(ApprovedGroup.status == "approved")
        )

        # Total errors in DB
        from database.models import ErrorEntry
        total_errors = await session.scalar(select(func.count()).select_from(ErrorEntry))

        # Resolution rate: OCR logs with a match / total OCR logs
        total_ocr = await session.scalar(select(func.count()).select_from(OCRLog))
        matched_ocr = await session.scalar(
            select(func.count()).where(OCRLog.matched_error_id != None)
        )
        resolution_rate = (matched_ocr / total_ocr * 100) if total_ocr else 0.0

    return OverviewStats(
        today_questions=today_q or 0,
        total_groups=total_groups or 0,
        approved_groups=approved_groups or 0,
        total_errors_in_db=total_errors or 0,
        resolution_rate_percent=round(resolution_rate, 1),
        avg_response_time_sec=None,  # conversation tracking required
    )


@router.get("/timeline", response_model=list[DailyPoint])
async def timeline(
    days: int = Query(7, ge=1, le=90),
    _admin: int = Depends(get_current_admin),
):
    now = datetime.now(timezone.utc)
    result = []

    async with get_session() as session:
        for i in range(days - 1, -1, -1):
            day_start = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)

            questions = await session.scalar(
                select(func.count()).where(
                    and_(
                        MessageClassification.created_at >= day_start,
                        MessageClassification.created_at < day_end,
                        MessageClassification.is_help_request == True,
                    )
                )
            ) or 0

            resolved = await session.scalar(
                select(func.count()).where(
                    and_(
                        OCRLog.created_at >= day_start,
                        OCRLog.created_at < day_end,
                        OCRLog.matched_error_id != None,
                    )
                )
            ) or 0

            result.append(DailyPoint(
                date=day_start.strftime("%Y-%m-%d"),
                questions=questions,
                resolved=resolved,
            ))

    return result


@router.get("/top-errors", response_model=list[TopError])
async def top_errors(
    limit: int = Query(10, ge=1, le=50),
    _admin: int = Depends(get_current_admin),
):
    async with get_session() as session:
        from database.models import ErrorEntry
        rows = await session.execute(
            select(
                OCRLog.matched_error_id,
                ErrorEntry.title_ru,
                ErrorEntry.title,
                func.count().label("cnt"),
            )
            .join(ErrorEntry, OCRLog.matched_error_id == ErrorEntry.id, isouter=True)
            .where(OCRLog.matched_error_id != None)
            .group_by(OCRLog.matched_error_id, ErrorEntry.title_ru, ErrorEntry.title)
            .order_by(func.count().desc())
            .limit(limit)
        )
        return [
            TopError(
                error_id=row.matched_error_id,
                title=row.title_ru or row.title or "—",
                count=row.cnt,
            )
            for row in rows
        ]


@router.get("/groups", response_model=list[GroupStat])
async def group_stats(_admin: int = Depends(get_current_admin)):
    async with get_session() as session:
        groups = await session.execute(
            select(ApprovedGroup).where(ApprovedGroup.status == "approved")
        )
        groups = groups.scalars().all()

        result = []
        for g in groups:
            questions = await session.scalar(
                select(func.count()).where(
                    and_(
                        MessageClassification.chat_id == g.chat_id,
                        MessageClassification.is_help_request == True,
                    )
                )
            ) or 0

            ai_resolved = await session.scalar(
                select(func.count()).where(
                    and_(
                        OCRLog.chat_id == g.chat_id,
                        OCRLog.matched_via.in_(["fuzzy_easyocr", "fuzzy_ai", "kb_match"]),
                    )
                )
            ) or 0

            support_resolved = await session.scalar(
                select(func.count()).where(
                    and_(
                        OCRLog.chat_id == g.chat_id,
                        OCRLog.matched_via == "vision_ai",
                    )
                )
            ) or 0

            result.append(GroupStat(
                chat_id=g.chat_id,
                title=g.title,
                questions=questions,
                resolved_by_ai=ai_resolved,
                resolved_by_support=support_resolved,
            ))

    return sorted(result, key=lambda x: x.questions, reverse=True)
