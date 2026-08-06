"""initial schema — errors & ocr_logs

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "errors",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("keywords", sa.ARRAY(sa.String), nullable=False, server_default="{}"),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("solution", sa.Text, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_errors_title", "errors", ["title"])

    op.create_table(
        "ocr_logs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("telegram_user", sa.BigInteger, nullable=False),
        sa.Column("telegram_username", sa.String(255), nullable=True),
        sa.Column("chat_id", sa.BigInteger, nullable=False),
        sa.Column("image_path", sa.String(512), nullable=False),
        sa.Column("detected_text", sa.Text, nullable=True),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column(
            "matched_error_id",
            sa.Integer,
            sa.ForeignKey("errors.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("match_score", sa.Float, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_ocr_logs_telegram_user", "ocr_logs", ["telegram_user"])
    op.create_index("ix_ocr_logs_chat_id", "ocr_logs", ["chat_id"])
    op.create_index("ix_ocr_logs_matched_error_id", "ocr_logs", ["matched_error_id"])


def downgrade() -> None:
    op.drop_index("ix_ocr_logs_matched_error_id", table_name="ocr_logs")
    op.drop_index("ix_ocr_logs_chat_id", table_name="ocr_logs")
    op.drop_index("ix_ocr_logs_telegram_user", table_name="ocr_logs")
    op.drop_table("ocr_logs")
    op.drop_index("ix_errors_title", table_name="errors")
    op.drop_table("errors")
