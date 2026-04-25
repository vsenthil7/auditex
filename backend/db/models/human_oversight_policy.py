"""
Auditex - HumanOversightPolicy ORM model.

One row per task_type. Defines whether human review is required, N-of-M quorum,
timeout behaviour. Mutable via PUT /api/v1/human-oversight-policies/{task_type}.
"""
from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class HumanOversightPolicy(Base, TimestampMixin):
    """Per-task-type policy for Article 14 human oversight."""
    __tablename__ = 'human_oversight_policies'

    task_type: Mapped[str] = mapped_column(String(100), primary_key=True)
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default='true')
    n_required: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default='1')
    m_total: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default='1')
    timeout_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    auto_commit_on_timeout: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default='false')

    def __repr__(self) -> str:
        return f'<HumanOversightPolicy {self.task_type} req={self.required} {self.n_required}/{self.m_total}>'
