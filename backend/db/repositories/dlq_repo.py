"""Auditex -- Dead Letter Queue repository (Phase 11 Item 3)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.dlq_entry import DLQEntry


async def create_entry(
    session: AsyncSession,
    *,
    task_id: uuid.UUID | None,
    source_queue: str,
    error_class: str,
    error_message: str,
    payload: dict | None = None,
    attempt_count: int = 0,
) -> DLQEntry:
    """INSERT a new dead-lettered entry."""
    entry = DLQEntry(
        task_id=task_id,
        source_queue=source_queue,
        error_class=error_class,
        error_message=error_message,
        payload=payload or {},
        attempt_count=attempt_count,
        status="PENDING",
    )
    session.add(entry)
    await session.flush()
    await session.refresh(entry)
    return entry


async def get_entry(session: AsyncSession, entry_id: uuid.UUID) -> DLQEntry | None:
    """SELECT a DLQ entry by primary key."""
    result = await session.execute(select(DLQEntry).where(DLQEntry.id == entry_id))
    return result.scalar_one_or_none()


async def list_entries(
    session: AsyncSession,
    *,
    status: str | None = None,
    limit: int = 100,
) -> Sequence[DLQEntry]:
    """LIST DLQ entries, newest first. Optional status filter."""
    stmt = select(DLQEntry).order_by(DLQEntry.created_at.desc())
    if status is not None:
        stmt = stmt.where(DLQEntry.status == status)
    stmt = stmt.limit(limit)
    result = await session.execute(stmt)
    return result.scalars().all()


async def mark_resolved(
    session: AsyncSession,
    entry_id: uuid.UUID,
    *,
    resolution_note: str | None = None,
) -> DLQEntry | None:
    """Mark an entry RESOLVED. Returns the updated entry, or None if not found."""
    entry = await get_entry(session, entry_id)
    if entry is None:
        return None
    entry.status = "RESOLVED"
    entry.resolved_at = datetime.now(timezone.utc)
    entry.resolution_note = resolution_note
    await session.flush()
    await session.refresh(entry)
    return entry


async def mark_retrying(
    session: AsyncSession,
    entry_id: uuid.UUID,
) -> DLQEntry | None:
    """Flip an entry to RETRYING and bump attempt_count."""
    entry = await get_entry(session, entry_id)
    if entry is None:
        return None
    entry.status = "RETRYING"
    entry.attempt_count = entry.attempt_count + 1
    await session.flush()
    await session.refresh(entry)
    return entry
