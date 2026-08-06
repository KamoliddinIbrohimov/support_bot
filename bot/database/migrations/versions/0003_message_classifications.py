"""message_classifications table for classifier tuning

Revision ID: 0003_message_classifications
Revises: 0002_users_i18n_vision
Create Date: 2026-08-04
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_message_classifications"
down_revision: Union[str, None] = "0002_users_i18n_vision"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "message_classifications",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("telegram_user", sa.BigInteger, nullable=False),
        sa.Column("telegram_username", sa.String(255), nullable=True),
        sa.Column("chat_id", sa.BigInteger, nullable=False),
        sa.Column("message_text", sa.String(500), nullable=True),
        sa.Column("language", sa.String(10), nullable=True),
        sa.Column("is_help_request", sa.Boolean, nullable=True),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column("action_taken", sa.String(30), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_msgcls_user", "message_classifications", ["telegram_user"])
    op.create_index("ix_msgcls_chat", "message_classifications", ["chat_id"])
    op.create_index("ix_msgcls_action", "message_classifications", ["action_taken"])


def downgrade() -> None:
    op.drop_index("ix_msgcls_action", table_name="message_classifications")
    op.drop_index("ix_msgcls_chat", table_name="message_classifications")
    op.drop_index("ix_msgcls_user", table_name="message_classifications")
    op.drop_table("message_classifications")
