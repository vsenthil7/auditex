"""
Auditex - HumanDecision ORM model.

Records each natural-person review on a task (Article 14 EU AI Act).
A task may collect multiple HumanDecision rows when its policy is N-of-M with N >= 2.
Quorum and finalisation logic lives in core/review/oversight_policy.py.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class HumanDecision(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A single human review decision on a task. Immutable once written."""
    __tablename__ = 'human_decisions'

    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('tasks.id'), nullable=False, index=True)
    decision: Mapped[str] = mapped_column(String(50), nullable=False)
    # APPROVE | REJECT | REQUEST_AMENDMENTS
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    reviewed_by: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    task = relationship('Task', back_populates='human_decisions')

    def __repr__(self) -> str:
        return f'<HumanDecision task={self.task_id} decision={self.decision} by={self.reviewed_by}>'
