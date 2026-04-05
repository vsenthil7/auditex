"""
Auditex -- Agent ORM model.
An Agent is any AI model or human actor registered in the system.
Every action in the audit trail is attributed to a registered Agent.
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utcnow


class Agent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Registry of all AI agents and human actors.
    Each agent has a cryptographic identity (public_key).
    Agents are never deleted -- they are deactivated.
    """
    __tablename__ = "agents"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    agent_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # "claude", "gpt4o", "human", "system"
    model_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    public_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    capabilities: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # JSON string of capability list
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    deactivated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    metadata_json: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # arbitrary metadata as JSON string

    # Relationships
    tasks_as_executor = relationship(
        "Task", back_populates="executor_agent", foreign_keys="Task.executor_agent_id"
    )

    def __repr__(self) -> str:
        return f"<Agent id={self.id} name={self.name} type={self.agent_type}>"
