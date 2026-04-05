"""initial schema -- all tables + audit_events tamper-proof policy

Revision ID: 0001
Revises:
Create Date: 2026-04-05
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------ agents
    op.create_table(
        "agents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("agent_type", sa.String(50), nullable=False),
        sa.Column("model_version", sa.String(100), nullable=True),
        sa.Column("public_key", sa.Text(), nullable=True),
        sa.Column("capabilities", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agents_agent_type", "agents", ["agent_type"])

    # ------------------------------------------------------------------ tasks
    op.create_table(
        "tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workflow_id", sa.String(255), nullable=True),
        sa.Column("task_type", sa.String(100), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="QUEUED"),
        sa.Column("submitted_by", sa.String(255), nullable=True),
        sa.Column("api_key_id", sa.String(255), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("executor_agent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("executor_output_json", sa.Text(), nullable=True),
        sa.Column("executor_confidence", sa.Numeric(4, 3), nullable=True),
        sa.Column("execution_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("execution_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("review_result_json", sa.Text(), nullable=True),
        sa.Column("consensus_result", sa.String(50), nullable=True),
        sa.Column("review_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("vertex_event_hash", sa.String(255), nullable=True),
        sa.Column("vertex_round", sa.Integer(), nullable=True),
        sa.Column("vertex_finalised_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("escalated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("escalation_reason", sa.String(500), nullable=True),
        sa.Column("human_resolution_json", sa.Text(), nullable=True),
        sa.Column("resolved_by", sa.String(255), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_reason", sa.String(500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["executor_agent_id"], ["agents.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tasks_status", "tasks", ["status"])
    op.create_index("ix_tasks_workflow_id", "tasks", ["workflow_id"])

    # --------------------------------------------------------------- audit_events
    op.create_table(
        "audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_agent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_type", sa.String(50), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("vertex_event_hash", sa.String(255), nullable=True),
        sa.Column("vertex_parent_hash", sa.String(255), nullable=True),
        sa.Column("vertex_round", sa.Integer(), nullable=True),
        sa.Column("vertex_finalised_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("vertex_proof_json", sa.Text(), nullable=True),
        sa.Column("sequence", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["actor_agent_id"], ["agents.id"]),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_events_event_type", "audit_events", ["event_type"])
    op.create_index("ix_audit_events_task_id", "audit_events", ["task_id"])

    # ------------------------------------------------------------------ reports
    op.create_table(
        "reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("narrative", sa.Text(), nullable=True),
        sa.Column("eu_ai_act_json", sa.Text(), nullable=True),
        sa.Column("schema_version", sa.String(50), nullable=False, server_default="eu_ai_act_v1"),
        sa.Column("org_signature", sa.Text(), nullable=True),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("signing_key_id", sa.String(255), nullable=True),
        sa.Column("vertex_event_hash", sa.String(255), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("generator_model", sa.String(100), nullable=True),
        sa.Column("export_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_exported_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_id"),
    )
    op.create_index("ix_reports_task_id", "reports", ["task_id"])

    # ============================================================
    # TAMPER-PROOF POLICY on audit_events
    # This is the most critical DDL in the entire system.
    # Blocks UPDATE and DELETE at the database level.
    # Any attempt raises: "permission denied -- audit_events is append-only"
    # Spec reference: S02.2, S03 backend/db/models/audit_event.py, MT-006
    # ============================================================
    op.execute("ALTER TABLE audit_events ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE audit_events FORCE ROW LEVEL SECURITY;")

    # Allow INSERT for all (application inserts events)
    op.execute("""
        CREATE POLICY audit_events_insert_only
        ON audit_events
        FOR INSERT
        WITH CHECK (true);
    """)

    # Allow SELECT for all (events must be readable for reports)
    op.execute("""
        CREATE POLICY audit_events_select_all
        ON audit_events
        FOR SELECT
        USING (true);
    """)

    # Block UPDATE -- no policy means no access (RLS default-deny)
    # Block DELETE -- same

    # Trigger to raise explicit error on any UPDATE attempt
    op.execute("""
        CREATE OR REPLACE FUNCTION audit_events_no_update()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'audit_events is append-only -- UPDATE is not permitted. Event ID: %', OLD.id;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER trg_audit_events_no_update
        BEFORE UPDATE ON audit_events
        FOR EACH ROW EXECUTE FUNCTION audit_events_no_update();
    """)

    # Trigger to raise explicit error on any DELETE attempt
    op.execute("""
        CREATE OR REPLACE FUNCTION audit_events_no_delete()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'audit_events is append-only -- DELETE is not permitted. Event ID: %', OLD.id;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER trg_audit_events_no_delete
        BEFORE DELETE ON audit_events
        FOR EACH ROW EXECUTE FUNCTION audit_events_no_delete();
    """)


def downgrade() -> None:
    # Remove tamper-proof triggers and policies first
    op.execute("DROP TRIGGER IF EXISTS trg_audit_events_no_delete ON audit_events;")
    op.execute("DROP TRIGGER IF EXISTS trg_audit_events_no_update ON audit_events;")
    op.execute("DROP FUNCTION IF EXISTS audit_events_no_delete();")
    op.execute("DROP FUNCTION IF EXISTS audit_events_no_update();")
    op.execute("DROP POLICY IF EXISTS audit_events_select_all ON audit_events;")
    op.execute("DROP POLICY IF EXISTS audit_events_insert_only ON audit_events;")
    op.execute("ALTER TABLE audit_events DISABLE ROW LEVEL SECURITY;")

    op.drop_table("reports")
    op.drop_table("audit_events")
    op.drop_table("tasks")
    op.drop_table("agents")
