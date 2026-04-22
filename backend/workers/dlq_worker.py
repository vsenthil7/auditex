"""Auditex -- Dead Letter Queue worker (Phase 11 Item 3).

When any worker task raises after its retry budget is exhausted, it calls
route_to_dlq() which persists a DLQEntry. A separate Celery task
redeliver_entry() can flip a DLQ entry back to RETRYING for manual replay.

This module is intentionally decoupled from the underlying queue broker --
the actual re-publish is handled by whoever imports redeliver_entry; here we
only own the DB side-effect.
"""
from __future__ import annotations

import asyncio
import logging
import uuid

from celery.utils.log import get_task_logger
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from db.repositories import dlq_repo
from workers.celery_app import celery_app

logger = get_task_logger(__name__)


def _make_session_factory():
    """Per-call engine/session factory (loop-safe for Celery)."""
    engine = create_async_engine(settings.DATABASE_URL, future=True)
    return async_sessionmaker(engine, expire_on_commit=False), engine


async def _route_async(
    task_id_str: str | None,
    source_queue: str,
    error_class: str,
    error_message: str,
    payload: dict,
    attempt_count: int,
) -> str:
    """Insert a DLQEntry. Returns the entry id as str."""
    Session, engine = _make_session_factory()
    try:
        async with Session() as session:
            task_uuid = uuid.UUID(task_id_str) if task_id_str else None
            entry = await dlq_repo.create_entry(
                session,
                task_id=task_uuid,
                source_queue=source_queue,
                error_class=error_class,
                error_message=error_message,
                payload=payload,
                attempt_count=attempt_count,
            )
            await session.commit()
            return str(entry.id)
    finally:
        await engine.dispose()


async def _redeliver_async(entry_id_str: str) -> str | None:
    """Flip an entry to RETRYING. Returns new status, or None if missing."""
    Session, engine = _make_session_factory()
    try:
        async with Session() as session:
            entry_uuid = uuid.UUID(entry_id_str)
            entry = await dlq_repo.mark_retrying(session, entry_uuid)
            if entry is None:
                return None
            await session.commit()
            return entry.status
    finally:
        await engine.dispose()


@celery_app.task(name="workers.dlq_worker.route_to_dlq", queue="dlq_queue")
def route_to_dlq(
    task_id: str | None,
    source_queue: str,
    error_class: str,
    error_message: str,
    payload: dict | None = None,
    attempt_count: int = 0,
) -> str:
    """Celery entrypoint: persist a DLQ entry. Returns the new entry id."""
    logger.warning(
        "DLQ route: task_id=%s source=%s error=%s",
        task_id, source_queue, error_class,
    )
    return asyncio.run(
        _route_async(
            task_id, source_queue, error_class, error_message,
            payload or {}, attempt_count,
        )
    )


@celery_app.task(name="workers.dlq_worker.redeliver_entry", queue="dlq_queue")
def redeliver_entry(entry_id: str) -> str | None:
    """Celery entrypoint: flip a DLQ entry to RETRYING for manual replay."""
    logger.info("DLQ redeliver: entry_id=%s", entry_id)
    return asyncio.run(_redeliver_async(entry_id))
