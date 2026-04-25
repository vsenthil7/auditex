"""
Auditex - HumanOversightPolicy + HumanDecision repository.
All DB access for Article 14 human oversight goes through here.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.human_oversight_policy import HumanOversightPolicy
from db.models.human_decision import HumanDecision

async def get_policy(session: AsyncSession, *, task_type: str) -> HumanOversightPolicy | None:
    result = await session.execute(select(HumanOversightPolicy).where(HumanOversightPolicy.task_type == task_type))
    return result.scalar_one_or_none()

async def list_policies(session: AsyncSession) -> list[HumanOversightPolicy]:
    result = await session.execute(select(HumanOversightPolicy).order_by(HumanOversightPolicy.task_type))
    return list(result.scalars().all())

async def upsert_policy(session: AsyncSession, *, task_type: str, required: bool, n_required: int, m_total: int, timeout_minutes: int | None, auto_commit_on_timeout: bool) -> HumanOversightPolicy:
    existing = await get_policy(session, task_type=task_type)
    if existing is None:
        existing = HumanOversightPolicy(task_type=task_type)
        session.add(existing)
    existing.required = required
    existing.n_required = n_required
    existing.m_total = m_total
    existing.timeout_minutes = timeout_minutes
    existing.auto_commit_on_timeout = auto_commit_on_timeout
    await session.flush()
    await session.refresh(existing)
    return existing

async def list_decisions_for_task(session: AsyncSession, *, task_id: uuid.UUID) -> list[HumanDecision]:
    result = await session.execute(select(HumanDecision).where(HumanDecision.task_id == task_id).order_by(HumanDecision.decided_at))
    return list(result.scalars().all())

async def insert_decision(session: AsyncSession, *, task_id: uuid.UUID, decision: str, reason: str, reviewed_by: str, decided_at: datetime) -> HumanDecision:
    row = HumanDecision(task_id=task_id, decision=decision, reason=reason, reviewed_by=reviewed_by, decided_at=decided_at)
    session.add(row)
    await session.flush()
    await session.refresh(row)
    return row

async def has_reviewed(session: AsyncSession, *, task_id: uuid.UUID, reviewed_by: str) -> bool:
    result = await session.execute(select(HumanDecision.id).where(HumanDecision.task_id == task_id, HumanDecision.reviewed_by == reviewed_by))
    return result.first() is not None
