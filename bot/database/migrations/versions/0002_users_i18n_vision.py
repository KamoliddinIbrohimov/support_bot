"""users table, bilingual error columns, ocr_logs.matched_via

Revision ID: 0002_users_i18n_vision
Revises: 0001_initial
Create Date: 2026-08-04

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0002_users_i18n_vision"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. users table ───────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("telegram_id", sa.BigInteger, primary_key=True),
        sa.Column("username", sa.String(255), nullable=True),
        sa.Column("language", sa.String(2), nullable=False, server_default="uz"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # ── 2. Bilingual columns on errors ────────────────────────────────────────
    for col in ("title_ru", "title_uz"):
        op.add_column("errors", sa.Column(col, sa.String(255), nullable=True))

    for col in ("keywords_ru", "keywords_uz"):
        op.add_column("errors", sa.Column(col, sa.ARRAY(sa.String), nullable=True))

    for col in ("description_ru", "description_uz", "solution_ru", "solution_uz"):
        op.add_column("errors", sa.Column(col, sa.Text, nullable=True))

    # Seed _ru columns from existing data so fallback always works
    op.execute(
        """
        UPDATE errors
        SET title_ru       = title,
            keywords_ru    = keywords,
            description_ru = description,
            solution_ru    = solution
        """
    )

    # ── 3. matched_via on ocr_logs ────────────────────────────────────────────
    op.add_column(
        "ocr_logs",
        sa.Column("matched_via", sa.String(20), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("ocr_logs", "matched_via")

    for col in ("solution_uz", "solution_ru", "description_uz", "description_ru",
                "keywords_uz", "keywords_ru", "title_uz", "title_ru"):
        op.drop_column("errors", col)

    op.drop_table("users")
