"""
Auditex -- Event repository.
INSERT ONLY. No update or delete methods exist in this file.
This is enforced here (in Python) AND at the database level (PostgreSQL trigger).

If you are reading this file and considering adding an update or delete method:
DO NOT. The append-only guarantee is the entire point of this system.
Any modification to audit_events is a compliance violation.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.audit_event import AuditEvent


async def insert_event(
    session: AsyncSession,
    *,
    event_type: str,
    task_id: uuid.UUID | None = None,
    actor_agent_id: uuid.UUID | None = None,
    actor_type: str | None = None,
    payload: dict | None = None,
    sequence: int = 0,
) -> AuditEvent:
    """
    INSERT a new audit event. This is the ONLY write operation permitted.
    No update_event(), no delete_event() -- they do not exist.

    The database trigger will also reject any UPDATE or DELETE at the SQL level,
    providing a second line of defence.
    """
    import json

    event = AuditEvent(
        event_type=event_type,
        task_id=task_id,
        actor_agent_id=actor_agent_id,
        actor_type=actor_type,
        payload_json=json.dumps(payload or {}),
        sequence=sequence,
    )
    session.add(event)
    await session.flush()
    await session.refresh(event)
    return event


async def get_events_for_task(
    session: AsyncSession,
    task_id: uuid.UUID,
) -> list[AuditEvent]:
    """
    Fetch all audit events for a given task, ordered by sequence then created_at.
    Read-only. Returns empty list if no events found.
    """
    result = await session.execute(
        select(AuditEvent)
        .where(AuditEvent.task_id == task_id)
        .order_by(AuditEvent.sequence.asc(), AuditEvent.created_at.asc())
    )
    return list(result.scalars().all())
