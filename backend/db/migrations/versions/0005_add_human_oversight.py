"""add human_oversight_policies + human_decisions tables (Article 14 HIL)

Revision ID: 0005
Revises: 0004
Create Date: 2026-04-25
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from alembic import op

revision: str = '0005'
down_revision: Union[str, None] = '0004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Per-task-type policy table
    op.create_table(
        'human_oversight_policies',
        sa.Column('task_type', sa.String(100), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('required', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('n_required', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('m_total', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('timeout_minutes', sa.Integer(), nullable=True),
        sa.Column('auto_commit_on_timeout', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.CheckConstraint('n_required <= m_total', name='check_quorum_le_total'),
    )

    # Each natural-person decision row
    op.create_table(
        'human_decisions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('task_id', UUID(as_uuid=True), sa.ForeignKey('tasks.id', ondelete='CASCADE'), nullable=False),
        sa.Column('decision', sa.String(50), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('reviewed_by', sa.String(255), nullable=False),
        sa.Column('decided_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_human_decisions_task_id', 'human_decisions', ['task_id'])
    op.create_index('ix_human_decisions_reviewed_by', 'human_decisions', ['reviewed_by'])

    # Seed default policies for the 3 known task types (admin can edit later)
    op.execute('''INSERT INTO human_oversight_policies (task_type, required, n_required, m_total, timeout_minutes, auto_commit_on_timeout, created_at, updated_at) VALUES ('contract_check', true, 1, 1, NULL, false, now(), now()), ('risk_analysis', true, 2, 3, NULL, false, now(), now()), ('document_review', true, 1, 1, 1440, true, now(), now())''')


def downgrade() -> None:
    op.drop_index('ix_human_decisions_reviewed_by', table_name='human_decisions')
    op.drop_index('ix_human_decisions_task_id', table_name='human_decisions')
    op.drop_table('human_decisions')
    op.drop_table('human_oversight_policies')
