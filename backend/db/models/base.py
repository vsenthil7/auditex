"""
Auditex -- SQLAlchemy declarative base and shared mixins.
All ORM models inherit from Base.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    """Adds created_at to any model. No updated_at -- audit tables are immutable."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )


class UUIDPrimaryKeyMixin:
    """UUID primary key -- never auto-increment integers in a compliance system."""
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
