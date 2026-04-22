"""add dlq_entries table

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-22
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "dlq_entries",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("task_id", UUID(as_uuid=True), nullable=True),
        sa.Column("source_queue", sa.String(128), nullable=False),
        sa.Column("error_class", sa.String(256), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=False),
        sa.Column("payload", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(32), nullable=False, server_default="PENDING"),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_note", sa.Text(), nullable=True),
    )
    op.create_index("ix_dlq_entries_task_id", "dlq_entries", ["task_id"])
    op.create_index("ix_dlq_entries_status", "dlq_entries", ["status"])


def downgrade() -> None:
    op.drop_index("ix_dlq_entries_status", table_name="dlq_entries")
    op.drop_index("ix_dlq_entries_task_id", table_name="dlq_entries")
    op.drop_table("dlq_entries")
