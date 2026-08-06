from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import BigInteger, Boolean, DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from database.connection import Base


class ApiKey(Base):
    """Per-project API keys for auth."""
    __tablename__ = "api_keys"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<ApiKey project={self.project_id}>"


class KBError(Base):
    """Knowledge base entry — error + solution with embedding for semantic search."""
    __tablename__ = "kb_errors"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    project_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    is_shared: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    solution: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str | None] = mapped_column(String(2), nullable=True)

    embedding: Mapped[list[float] | None] = mapped_column(Vector(768), nullable=True)

    # 'manual' | 'ai_generated' | 'learned_from_support'
    source: Mapped[str] = mapped_column(String(30), nullable=False, default="manual")
    # 'pending' | 'verified' | 'rejected'
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)

    resolution_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    verified_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<KBError id={self.id} project={self.project_id} status={self.status}>"
