from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    ARRAY,
    BigInteger,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.connection import Base


class User(Base):
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    language: Mapped[str] = mapped_column(String(2), nullable=False, server_default="uz")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<User id={self.telegram_id} lang={self.language}>"


class ErrorEntry(Base):
    __tablename__ = "errors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Original columns (kept for backward-compat; migrate → _ru via migration)
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    keywords: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    solution: Mapped[str] = mapped_column(Text, nullable=False)

    # Bilingual columns — _ru seeded from originals via migration
    title_ru: Mapped[str | None] = mapped_column(String(255), nullable=True)
    title_uz: Mapped[str | None] = mapped_column(String(255), nullable=True)
    keywords_ru: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    keywords_uz: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    description_ru: Mapped[str | None] = mapped_column(Text, nullable=True)
    description_uz: Mapped[str | None] = mapped_column(Text, nullable=True)
    solution_ru: Mapped[str | None] = mapped_column(Text, nullable=True)
    solution_uz: Mapped[str | None] = mapped_column(Text, nullable=True)

    solution_video_file_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    solution_image_file_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    logs: Mapped[list["OCRLog"]] = relationship(
        back_populates="matched_error",
        cascade="save-update, merge",
        passive_deletes=True,
    )

    def get_title(self, lang: str) -> str:
        if lang == "uz" and self.title_uz:
            return self.title_uz
        return self.title_ru or self.title

    def get_keywords(self, lang: str) -> list[str]:
        if lang == "uz" and self.keywords_uz:
            return self.keywords_uz
        return self.keywords_ru or self.keywords

    def get_solution(self, lang: str) -> str:
        if lang == "uz" and self.solution_uz:
            return self.solution_uz
        return self.solution_ru or self.solution

    def get_description(self, lang: str) -> str | None:
        if lang == "uz" and self.description_uz:
            return self.description_uz
        return self.description_ru or self.description

    def __repr__(self) -> str:
        return f"<ErrorEntry id={self.id} title={self.title!r}>"


class ApprovedGroup(Base):
    """Guruhlar whitelistsi — pending/approved/rejected."""
    __tablename__ = "approved_groups"

    chat_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    chat_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    added_by_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    added_by_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    added_by_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # 'pending' | 'approved' | 'rejected'
    status: Mapped[str] = mapped_column(String(10), nullable=False, server_default="pending")
    approved_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<ApprovedGroup chat_id={self.chat_id} status={self.status}>"


class HelpKeyword(Base):
    """Self-learning keyword list — phrase confirmed as help request by AI."""
    __tablename__ = "help_keywords"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    phrase: Mapped[str] = mapped_column(String(200), nullable=False, unique=True, index=True)
    source: Mapped[str] = mapped_column(String(10), nullable=False, server_default="ai")  # 'ai' | 'manual'
    hit_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<HelpKeyword id={self.id} phrase={self.phrase!r} hits={self.hit_count}>"


class MessageClassification(Base):
    """Log of every group message classified by Step 1, for threshold tuning."""
    __tablename__ = "message_classifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_user: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    telegram_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    message_text: Mapped[str | None] = mapped_column(String(500), nullable=True)
    language: Mapped[str | None] = mapped_column(String(10), nullable=True)
    is_help_request: Mapped[bool | None] = mapped_column(nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    # 'silent' | 'silent_uncertain' | 'asked_for_screenshot' | 'answered' | 'out_of_scope'
    action_taken: Mapped[str | None] = mapped_column(String(30), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<MsgCls id={self.id} help={self.is_help_request} conf={self.confidence} action={self.action_taken}>"


class OCRLog(Base):
    __tablename__ = "ocr_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_user: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    telegram_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    image_path: Mapped[str] = mapped_column(String(512), nullable=False)
    detected_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    matched_error_id: Mapped[int | None] = mapped_column(
        ForeignKey("errors.id", ondelete="SET NULL"), nullable=True, index=True
    )
    match_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    matched_via: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    matched_error: Mapped[ErrorEntry | None] = relationship(back_populates="logs")

    def __repr__(self) -> str:
        return f"<OCRLog id={self.id} user={self.telegram_user} via={self.matched_via}>"
