"""
Auditex -- Retry handler and DLQ routing.
Used by the execution worker to manage failures.

Backoff schedule: 1s, 2s, 4s (max 3 attempts total).
On exhaustion: task is marked FAILED and routed to DLQ.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from db.repositories import event_repo, task_repo

logger = logging.getLogger(__name__)

# Backoff schedule: index 0 = after attempt 1 fails, etc.
_BACKOFF_SCHEDULE = [1.0, 2.0, 4.0]


async def exponential_backoff(attempt: int) -> None:
    """
    Sleep for the configured backoff duration for the given attempt number.
    attempt is 1-indexed (attempt=1 -> sleep 1s, attempt=2 -> sleep 2s, etc.)
    """
    index = min(attempt - 1, len(_BACKOFF_SCHEDULE) - 1)
    delay = _BACKOFF_SCHEDULE[index]
    logger.debug("Backoff: attempt=%d sleeping=%.1fs", attempt, delay)
    await asyncio.sleep(delay)


async def route_to_dlq(
    session: AsyncSession,
    task_id: uuid.UUID,
    reason: str,
) -> None:
    """
    Mark a task as FAILED and record a DLQ audit event.

    This is called after all retries are exhausted.
    The task remains in the DB -- it is never deleted.
    An AuditEvent with event_type="task_failed_dlq" is inserted.
    """
    now = datetime.now(timezone.utc)

    await task_repo.update_task_status(
        session,
        task_id=task_id,
        status="FAILED",
        failed_at=now,
        failure_reason=reason[:500],
    )

    await event_repo.insert_event(
        session,
        task_id=task_id,
        event_type="task_failed_dlq",
        payload={
            "reason": reason,
            "routed_to_dlq_at": now.isoformat(),
        },
    )

    logger.error(
        "Task %s routed to DLQ. Reason: %s", task_id, reason
    )
