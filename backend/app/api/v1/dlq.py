"""Auditex -- Dead Letter Queue API routes (Phase 11 Item 3)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.middleware.auth import require_api_key
from db.connection import get_db_session
from db.repositories import dlq_repo

router = APIRouter(prefix="/dlq", tags=["dlq"])


def _entry_to_dict(entry) -> dict:
    """Serialise a DLQEntry ORM object to a JSON-safe dict."""
    return {
        "id": str(entry.id),
        "task_id": str(entry.task_id) if entry.task_id else None,
        "source_queue": entry.source_queue,
        "error_class": entry.error_class,
        "error_message": entry.error_message,
        "payload": entry.payload,
        "attempt_count": entry.attempt_count,
        "status": entry.status,
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
        "resolved_at": entry.resolved_at.isoformat() if entry.resolved_at else None,
        "resolution_note": entry.resolution_note,
    }


@router.get("/", response_model=dict, summary="List DLQ entries")
async def list_dlq_entries(
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=500),
    _key_meta: dict = Depends(require_api_key),
    session=Depends(get_db_session),
):
    entries = await dlq_repo.list_entries(session, status=status_filter, limit=limit)
    return {
        "count": len(entries),
        "entries": [_entry_to_dict(e) for e in entries],
    }


@router.get("/{entry_id}", response_model=dict, summary="Get one DLQ entry")
async def get_dlq_entry(
    entry_id: uuid.UUID,
    _key_meta: dict = Depends(require_api_key),
    session=Depends(get_db_session),
):
    entry = await dlq_repo.get_entry(session, entry_id)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"DLQ entry {entry_id} not found.",
        )
    return _entry_to_dict(entry)


@router.post("/{entry_id}/retry", response_model=dict, summary="Flip an entry to RETRYING")
async def retry_dlq_entry(
    entry_id: uuid.UUID,
    _key_meta: dict = Depends(require_api_key),
    session=Depends(get_db_session),
):
    entry = await dlq_repo.mark_retrying(session, entry_id)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"DLQ entry {entry_id} not found.",
        )
    await session.commit()
    return _entry_to_dict(entry)


@router.post("/{entry_id}/resolve", response_model=dict, summary="Mark an entry RESOLVED")
async def resolve_dlq_entry(
    entry_id: uuid.UUID,
    note: str | None = Query(default=None, max_length=2000),
    _key_meta: dict = Depends(require_api_key),
    session=Depends(get_db_session),
):
    entry = await dlq_repo.mark_resolved(session, entry_id, resolution_note=note)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"DLQ entry {entry_id} not found.",
        )
    await session.commit()
    return _entry_to_dict(entry)
