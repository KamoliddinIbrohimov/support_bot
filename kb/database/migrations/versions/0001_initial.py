"""Initial KB schema — api_keys + kb_errors with pgvector

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-04
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # ── api_keys ─────────────────────────────────────────────────────────────
    op.create_table(
        "api_keys",
        sa.Column("key", sa.String(100), primary_key=True),
        sa.Column("project_id", sa.String(100), nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_api_keys_project", "api_keys", ["project_id"])

    # ── kb_errors ─────────────────────────────────────────────────────────────
    op.create_table(
        "kb_errors",
        sa.Column("id", sa.UUID, primary_key=True),
        sa.Column("project_id", sa.String(100), nullable=False),
        sa.Column("is_shared", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("title", sa.Text, nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("solution", sa.Text, nullable=False),
        sa.Column("language", sa.String(2), nullable=True),
        sa.Column("embedding", sa.Text, nullable=True),   # vector type added via raw SQL below
        sa.Column("source", sa.String(30), nullable=False, server_default="manual"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("resolution_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("verified_by", sa.BigInteger, nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Replace embedding column with proper vector type
    op.execute("ALTER TABLE kb_errors DROP COLUMN embedding")
    op.execute("ALTER TABLE kb_errors ADD COLUMN embedding vector(768)")

    # HNSW index for fast cosine similarity search
    op.execute(
        "CREATE INDEX kb_errors_embedding_idx ON kb_errors "
        "USING hnsw (embedding vector_cosine_ops)"
    )

    op.create_index("ix_kb_errors_project", "kb_errors", ["project_id"])
    op.create_index("ix_kb_errors_status", "kb_errors", ["status"])
    op.create_index("ix_kb_errors_shared", "kb_errors", ["is_shared"])


def downgrade() -> None:
    op.drop_table("kb_errors")
    op.drop_table("api_keys")
    op.execute("DROP EXTENSION IF EXISTS vector")
