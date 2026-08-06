"""Add solution_image_file_id to errors table

Revision ID: 0007_image_support
Revises: 0006_approved_groups
Create Date: 2026-08-06
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0007_image_support"
down_revision = "0006_approved_groups"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "errors",
        sa.Column("solution_image_file_id", sa.String(255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("errors", "solution_image_file_id")
