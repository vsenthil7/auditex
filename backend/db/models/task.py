"""
Auditex -- Task ORM model.
A Task is a unit of work submitted by a client system for AI execution and review.
Tasks progress through a strict lifecycle: QUEUED -> EXECUTING -> REVIEWING
  -> FINALISING -> COMPLETED | FAILED | ESCALATED
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Task(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Core task record. Immutable once COMPLETED.
    The executor_output and review_result fields are written once and never updated.
    """
    __tablename__ = "tasks"

    # Identity
    workflow_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    task_type: Mapped[str] = mapped_column(String(100), nullable=False)
    # e.g. "document_review", "risk_analysis", "contract_check"

    # Status lifecycle
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="QUEUED", index=True
    )
    # QUEUED | EXECUTING | REVIEWING | FINALISING | COMPLETED | FAILED | ESCALATED

    # Submission
    submitted_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    api_key_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    # Raw task payload as JSON string

    # Execution
    executor_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True
    )
    executor_output_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    executor_confidence: Mapped[float | None] = mapped_column(Numeric(4, 3), nullable=True)
    execution_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    execution_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Review
    review_result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Full review package: 3 verdicts + commitment proofs + consensus result
    consensus_result: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # "3_OF_3_APPROVE" | "2_OF_3_APPROVE" | "REJECTED" | "ESCALATED"
    review_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Vertex consensus
    vertex_event_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    vertex_round: Mapped[int | None] = mapped_column(Integer, nullable=True)
    vertex_finalised_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Escalation
    escalated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    escalation_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    human_resolution_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Completion
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    failed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    failure_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Relationships
    executor_agent = relationship(
        "Agent", back_populates="tasks_as_executor", foreign_keys=[executor_agent_id]
    )
    audit_events = relationship("AuditEvent", back_populates="task")
    report = relationship("Report", back_populates="task", uselist=False)

    def __repr__(self) -> str:
        return f"<Task id={self.id} type={self.task_type} status={self.status}>"
