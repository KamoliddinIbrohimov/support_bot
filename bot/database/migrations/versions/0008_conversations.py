"""Add conversations table for statistics tracking

Revision ID: 0008_conversations
Revises: 0007_image_support
Create Date: 2026-08-08
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0008_conversations"
down_revision = "0007_image_support"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("group_id", sa.BigInteger(), nullable=False, index=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False, index=True),
        sa.Column("error_id", sa.Integer(), sa.ForeignKey("errors.id", ondelete="SET NULL"), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by", sa.String(20), nullable=True),
        sa.Column("message_count", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_index("ix_conversations_group_id", "conversations", ["group_id"])
    op.create_index("ix_conversations_user_id", "conversations", ["user_id"])
    op.create_index("ix_conversations_started_at", "conversations", ["started_at"])


def downgrade() -> None:
    op.drop_table("conversations")
