"""help_keywords self-learning table with seed data

Revision ID: 0004_help_keywords
Revises: 0003_message_classifications
Create Date: 2026-08-04
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_help_keywords"
down_revision: Union[str, None] = "0003_message_classifications"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Initial seed — common help phrases in uz/ru
SEED_PHRASES = [
    # Uzbek
    "yordam", "yordam kerak", "yordam bering", "xato", "xatolik",
    "ishlamayapti", "muammo", "kassa ishlamaydi", "chiqyapti xato",
    "qanday qilaman", "nima qilaman", "tushunmadim",
    # Russian
    "помогите", "помощь", "ошибка", "не работает", "проблема",
    "зависло", "завис", "не печатает", "не сканирует",
    "нет соединения", "connection error", "что делать",
    "как исправить", "не могу", "не получается",
    # Mixed / technical
    "error", "не найден", "topilmadi", "ulanmayapti",
    "chek chiqmayapti", "skaner ishlamayapti",
]


def upgrade() -> None:
    op.create_table(
        "help_keywords",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("phrase", sa.String(200), nullable=False, unique=True),
        sa.Column("source", sa.String(10), nullable=False, server_default="manual"),
        sa.Column("hit_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_help_keywords_phrase", "help_keywords", ["phrase"])

    # Seed initial phrases
    op.bulk_insert(
        sa.table(
            "help_keywords",
            sa.column("phrase", sa.String),
            sa.column("source", sa.String),
        ),
        [{"phrase": p, "source": "manual"} for p in SEED_PHRASES],
    )


def downgrade() -> None:
    op.drop_index("ix_help_keywords_phrase", table_name="help_keywords")
    op.drop_table("help_keywords")
