"""Auditex -- Dead Letter Queue entry model (Phase 11 Item 3)."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, Integer
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from db.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class DLQEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A dead-lettered task/message awaiting triage."""
    __tablename__ = "dlq_entries"

    task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True,
    )
    source_queue: Mapped[str] = mapped_column(String(128), nullable=False)
    error_class: Mapped[str] = mapped_column(String(256), nullable=False)
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="PENDING", index=True,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<DLQEntry id={self.id} source={self.source_queue} status={self.status}>"
