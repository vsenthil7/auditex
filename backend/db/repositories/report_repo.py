"""
Auditex -- Report repository.
All database access for the reports table goes through here.

Methods:
  create_report()            -- INSERT new Report record
  get_report_by_task_id()    -- SELECT report by task UUID
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.report import Report


async def create_report(
    session: AsyncSession,
    *,
    task_id: uuid.UUID,
    narrative: str,
    eu_ai_act_json: str,
    schema_version: str = "poc_report_v1",
    vertex_event_hash: str | None = None,
    generated_at: datetime,
    generator_model: str,
) -> Report:
    """
    Insert a new Report record.
    Returns the persisted Report ORM object.
    """
    report = Report(
        task_id=task_id,
        narrative=narrative,
        eu_ai_act_json=eu_ai_act_json,
        schema_version=schema_version,
        vertex_event_hash=vertex_event_hash,
        generated_at=generated_at,
        generator_model=generator_model,
    )
    session.add(report)
    await session.flush()
    await session.refresh(report)
    return report


async def get_report_by_task_id(
    session: AsyncSession,
    task_id: uuid.UUID,
) -> Report | None:
    """
    Fetch a Report by task UUID. Returns None if not found.
    """
    result = await session.execute(
        select(Report).where(Report.task_id == task_id)
    )
    return result.scalar_one_or_none()
