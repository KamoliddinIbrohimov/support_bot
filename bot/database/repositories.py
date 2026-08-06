from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import ApprovedGroup, ErrorEntry, HelpKeyword, MessageClassification, OCRLog, User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, telegram_id: int) -> User | None:
        return await self._session.get(User, telegram_id)

    async def get_or_create(
        self,
        *,
        telegram_id: int,
        username: str | None,
        language_code: str | None,
    ) -> User:
        """Fetch existing user or create with auto-detected language.

        language_code from Telegram: 'ru' → 'ru', anything else → 'uz'.
        """
        user = await self.get(telegram_id)
        if user is None:
            lang = "ru" if language_code == "ru" else "uz"
            user = User(telegram_id=telegram_id, username=username, language=lang)
            self._session.add(user)
            await self._session.flush()
        else:
            # Keep username fresh
            if user.username != username:
                user.username = username
                user.updated_at = datetime.now(tz=timezone.utc)
        return user

    async def set_language(self, telegram_id: int, language: str) -> User | None:
        user = await self.get(telegram_id)
        if user is None:
            return None
        user.language = language
        user.updated_at = datetime.now(tz=timezone.utc)
        return user

    async def get_language(self, telegram_id: int) -> str:
        user = await self.get(telegram_id)
        return user.language if user else "uz"


class ErrorRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        title: str,
        keywords: list[str],
        solution: str,
        description: str | None = None,
        title_ru: str | None = None,
        title_uz: str | None = None,
        keywords_ru: list[str] | None = None,
        keywords_uz: list[str] | None = None,
        solution_ru: str | None = None,
        solution_uz: str | None = None,
        description_ru: str | None = None,
        description_uz: str | None = None,
    ) -> ErrorEntry:
        entry = ErrorEntry(
            title=title,
            keywords=keywords,
            solution=solution,
            description=description,
            # Seed _ru from primary if not explicitly given
            title_ru=title_ru or title,
            title_uz=title_uz,
            keywords_ru=keywords_ru or keywords,
            keywords_uz=keywords_uz,
            solution_ru=solution_ru or solution,
            solution_uz=solution_uz,
            description_ru=description_ru or description,
            description_uz=description_uz,
        )
        self._session.add(entry)
        await self._session.flush()
        return entry

    async def list_all(self) -> Sequence[ErrorEntry]:
        result = await self._session.execute(select(ErrorEntry).order_by(ErrorEntry.id))
        return result.scalars().all()

    async def get_by_id(self, error_id: int) -> ErrorEntry | None:
        return await self._session.get(ErrorEntry, error_id)

    async def update_video(self, error_id: int, file_id: str) -> ErrorEntry | None:
        entry = await self.get_by_id(error_id)
        if entry is None:
            return None
        entry.solution_video_file_id = file_id
        await self._session.flush()
        return entry

    async def delete(self, error_id: int) -> bool:
        entry = await self.get_by_id(error_id)
        if entry is None:
            return False
        await self._session.delete(entry)
        return True


class HelpKeywordRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_phrases(self) -> list[str]:
        result = await self._session.execute(select(HelpKeyword.phrase))
        return list(result.scalars().all())

    async def add(self, phrase: str, source: str = "ai") -> None:
        """Add phrase if not already exists. Silently skip duplicates."""
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        stmt = pg_insert(HelpKeyword).values(phrase=phrase, source=source)
        stmt = stmt.on_conflict_do_update(
            index_elements=["phrase"],
            set_={"hit_count": HelpKeyword.hit_count + 1},
        )
        await self._session.execute(stmt)

    async def increment_hit(self, phrase: str) -> None:
        from sqlalchemy import update
        await self._session.execute(
            update(HelpKeyword)
            .where(HelpKeyword.phrase == phrase)
            .values(hit_count=HelpKeyword.hit_count + 1)
        )


class MessageClassificationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        telegram_user: int,
        telegram_username: str | None,
        chat_id: int,
        message_text: str | None,
        language: str | None,
        is_help_request: bool | None,
        confidence: float | None,
        action_taken: str | None,
    ) -> MessageClassification:
        row = MessageClassification(
            telegram_user=telegram_user,
            telegram_username=telegram_username,
            chat_id=chat_id,
            message_text=(message_text or "")[:500],
            language=language,
            is_help_request=is_help_request,
            confidence=confidence,
            action_taken=action_taken,
        )
        self._session.add(row)
        await self._session.flush()
        return row


class OCRLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        telegram_user: int,
        telegram_username: str | None,
        chat_id: int,
        image_path: str,
        detected_text: str | None,
        confidence: float | None,
        matched_error_id: int | None,
        match_score: float | None,
        matched_via: str | None = None,
    ) -> OCRLog:
        log = OCRLog(
            telegram_user=telegram_user,
            telegram_username=telegram_username,
            chat_id=chat_id,
            image_path=image_path,
            detected_text=detected_text,
            confidence=confidence,
            matched_error_id=matched_error_id,
            match_score=match_score,
            matched_via=matched_via,
        )
        self._session.add(log)
        await self._session.flush()
        return log

    async def list_recent(self, limit: int = 50) -> Sequence[OCRLog]:
        result = await self._session.execute(
            select(OCRLog).order_by(OCRLog.created_at.desc()).limit(limit)
        )
        return result.scalars().all()


class GroupRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert(
        self,
        *,
        chat_id: int,
        title: str | None,
        username: str | None,
        chat_type: str | None,
        added_by_id: int | None,
        added_by_name: str | None,
        added_by_username: str | None,
    ) -> ApprovedGroup:
        group = await self._session.get(ApprovedGroup, chat_id)
        if group is None:
            group = ApprovedGroup(
                chat_id=chat_id,
                title=title,
                username=username,
                chat_type=chat_type,
                added_by_id=added_by_id,
                added_by_name=added_by_name,
                added_by_username=added_by_username,
                status="pending",
            )
            self._session.add(group)
        else:
            group.title = title
            group.username = username
            group.updated_at = datetime.now(tz=timezone.utc)
        await self._session.flush()
        return group

    async def get(self, chat_id: int) -> ApprovedGroup | None:
        return await self._session.get(ApprovedGroup, chat_id)

    async def approve(self, chat_id: int, approved_by: int) -> ApprovedGroup | None:
        group = await self.get(chat_id)
        if group is None:
            return None
        group.status = "approved"
        group.approved_by = approved_by
        group.updated_at = datetime.now(tz=timezone.utc)
        await self._session.flush()
        return group

    async def reject(self, chat_id: int, rejected_by: int) -> ApprovedGroup | None:
        group = await self.get(chat_id)
        if group is None:
            return None
        group.status = "rejected"
        group.approved_by = rejected_by
        group.updated_at = datetime.now(tz=timezone.utc)
        await self._session.flush()
        return group

    async def is_approved(self, chat_id: int) -> bool:
        group = await self.get(chat_id)
        return group is not None and group.status == "approved"

    async def list_pending(self) -> Sequence[ApprovedGroup]:
        result = await self._session.execute(
            select(ApprovedGroup)
            .where(ApprovedGroup.status == "pending")
            .order_by(ApprovedGroup.created_at.desc())
        )
        return result.scalars().all()

    async def list_approved(self) -> Sequence[ApprovedGroup]:
        result = await self._session.execute(
            select(ApprovedGroup).where(ApprovedGroup.status == "approved")
        )
        return result.scalars().all()
