"""approved_groups table for group whitelist

Revision ID: 0006_approved_groups
Revises: 0005_video_support
Create Date: 2026-08-06
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006_approved_groups"
down_revision: Union[str, None] = "0005_video_support"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "approved_groups",
        sa.Column("chat_id", sa.BigInteger, primary_key=True),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("username", sa.String(255), nullable=True),
        sa.Column("chat_type", sa.String(20), nullable=True),
        sa.Column("added_by_id", sa.BigInteger, nullable=True),
        sa.Column("added_by_name", sa.String(255), nullable=True),
        sa.Column("added_by_username", sa.String(255), nullable=True),
        sa.Column(
            "status",
            sa.String(10),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("approved_by", sa.BigInteger, nullable=True),
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


def downgrade() -> None:
    op.drop_table("approved_groups")
