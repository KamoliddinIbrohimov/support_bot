"""Add solution_video_file_id to errors table

Revision ID: 0005_video_support
Revises: 0004_help_keywords
Create Date: 2026-08-06
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005_video_support"
down_revision: Union[str, None] = "0004_help_keywords"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "errors",
        sa.Column("solution_video_file_id", sa.String(255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("errors", "solution_video_file_id")
