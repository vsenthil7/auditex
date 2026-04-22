"""Auditex -- Events API routes (Phase 12 Step 3a, 1 endpoint).

Exposes third-party proof verification over HTTP, wrapping the
:mod:`core.consensus.proof_verifier` module that was shipped in
Phase 11 Item 2 but was not previously wired to a route.

Route:
    GET /api/v1/events/{task_id}/verify

Returns a JSON envelope suitable for rendering in the frontend
VerifySignatureDialog. Never raises on a verification mismatch --
a mismatch is returned as ``{"verified": false, "reason": "..."}``.
The only 4xx raised is 404 when the task has no Vertex event hash.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.api.middleware.auth import require_api_key
from core.consensus.proof_verifier import (
    EmptyEventChain,
    verify_task_proof,
)
from db.connection import get_db_session
from db.models.task import Task
from db.repositories import event_repo

router = APIRouter(prefix="/events", tags=["events"])


@router.get(
    "/{task_id}/verify",
    response_model=dict,
    summary="Third-party verification of a task's Vertex proof",
)
async def verify_task_proof_endpoint(
    task_id: uuid.UUID,
    _key_meta: dict = Depends(require_api_key),
    session=Depends(get_db_session),
):
    """Re-hash the event chain for ``task_id`` and compare against the
    Vertex event-hash stored on the Task row."""
    task = (
        await session.execute(select(Task).where(Task.id == task_id))
    ).scalar_one_or_none()
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found.",
        )
    expected = task.vertex_event_hash or ""
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Task {task_id} has no Vertex event hash -- not yet "
                "finalised, or proof was never committed."
            ),
        )

    events = await event_repo.get_events_for_task(session, task_id)
    try:
        result = verify_task_proof(events, expected)
    except EmptyEventChain:
        return {
            "task_id": str(task_id),
            "verified": False,
            "expected_hash": expected,
            "computed_hash": "",
            "event_count": 0,
            "reason": "event chain is empty -- nothing to hash",
            "checks": [
                {"name": "has_expected_hash", "ok": True},
                {"name": "has_events", "ok": False},
                {"name": "chain_hash_matches", "ok": False},
            ],
        }

    checks = [
        {"name": "has_expected_hash", "ok": True},
        {"name": "has_events", "ok": result.event_count > 0},
        {"name": "chain_hash_matches", "ok": result.verified},
    ]
    return {
        "task_id": str(task_id),
        "verified": result.verified,
        "expected_hash": result.expected_hash,
        "computed_hash": result.computed_hash,
        "event_count": result.event_count,
        "reason": result.reason,
        "checks": checks,
    }
