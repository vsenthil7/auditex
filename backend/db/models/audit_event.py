"""
Auditex -- AuditEvent ORM model.
THE most critical table in the system.

Rules (enforced at DB level via migration):
  - INSERT only. No UPDATE. No DELETE.
  - Row Security Policy blocks any attempt to modify existing rows.
  - Every event carries the Vertex proof: round number + event hash + parent hash.

This is the tamper-proof append-only audit log described in spec S02.2 and S03.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utcnow


class AuditEvent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Append-only audit event. Written once, never modified.
    Every significant action in the system produces an AuditEvent.
    """
    __tablename__ = "audit_events"

    # Event classification
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    # e.g. "task_submitted", "task_executed", "review_completed",
    #      "consensus_reached", "report_generated", "human_escalation",
    #      "human_override", "security_violation", "export_downloaded"

    # Task association (nullable -- some events are system-level)
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=True, index=True
    )

    # Actor who caused this event
    actor_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True
    )
    actor_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # "claude" | "gpt4o" | "human" | "system"

    # Event payload
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    # Full event data as JSON string

    # Vertex consensus proof -- set once Vertex finalises the event
    vertex_event_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    vertex_parent_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    vertex_round: Mapped[int | None] = mapped_column(Integer, nullable=True)
    vertex_finalised_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    vertex_proof_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Full Vertex cryptographic proof as JSON

    # Sequence within this task (for ordering before Vertex finalisation)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relationships
    task = relationship("Task", back_populates="audit_events")

    def __repr__(self) -> str:
        return f"<AuditEvent id={self.id} type={self.event_type} task={self.task_id}>"
