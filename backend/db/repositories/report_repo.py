"""
Auditex -- Report repository.
All database access for the reports table goes through here.

Methods:
  create_report()            -- INSERT new Report record
  get_report_by_task_id()    -- SELECT report by task UUID
  sign_report()              -- persist an export signature on an existing Report
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

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


async def sign_report(
    session: AsyncSession,
    task_id: uuid.UUID,
    *,
    signature_hex: str,
    signing_key_id: str,
    signed_at: datetime | None = None,
) -> Report | None:
    """
    Persist an HMAC export signature on the Report for ``task_id``.

    - Returns the updated Report on success.
    - Returns None if no Report exists for the task (caller decides 404 vs create).
    - ``signed_at`` defaults to now (UTC) if not supplied.

    This function does NOT compute or verify the signature -- it only stores
    the values. Signing/verification live in core.reporting.export_signer.
    The separation keeps crypto out of the data layer.
    """
    report = await get_report_by_task_id(session, task_id)
    if report is None:
        return None

    report.org_signature = signature_hex
    report.signing_key_id = signing_key_id
    report.signed_at = signed_at or datetime.now(timezone.utc)

    await session.flush()
    await session.refresh(report)
    return report
