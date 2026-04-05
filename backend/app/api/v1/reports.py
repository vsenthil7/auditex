"""
Auditex -- Reports routes (Phase 6).

GET /api/v1/reports/{task_id}
    Returns the full PoC report for a completed task.
    Includes: plain_english_summary, eu_ai_act, vertex_proof,
              schema_version, generated_at, report_available.

GET /api/v1/reports/{task_id}/export?format=eu_ai_act
    Returns the structured EU AI Act export dict plus summary and vertex proof.

Both routes require X-API-Key authentication.
"""
from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.middleware.auth import require_api_key
from db.connection import get_db_session
from db.repositories import report_repo, task_repo

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get(
    "/{task_id}",
    response_model=dict,
    summary="Get PoC report for a completed task",
)
async def get_report(
    task_id: uuid.UUID,
    _key_meta: dict = Depends(require_api_key),
    session=Depends(get_db_session),
):
    """
    MT-007: Return the full PoC report for a completed task.

    Response shape:
    {
      "task_id": "<uuid>",
      "schema_version": "poc_report_v1",
      "generated_at": "<ISO timestamp>",
      "plain_english_summary": "<non-empty string>",
      "eu_ai_act": {
        "article_9_risk_management": {...},
        "article_13_transparency": {...},
        "article_17_quality_management": {...}
      },
      "vertex_proof": {
        "event_hash": "<64-char hex>",
        "round": <int>,
        "finalised_at": "<ISO timestamp>"
      },
      "report_available": true
    }
    """
    # Verify task exists
    task = await task_repo.get_task(session, task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found.",
        )

    if task.status != "COMPLETED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Task {task_id} is not COMPLETED (status={task.status}). "
                   "Report is only available for COMPLETED tasks.",
        )

    report = await report_repo.get_report_by_task_id(session, task_id)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report for task {task_id} not yet available. "
                   "Retry in a few seconds.",
        )

    # Deserialise EU AI Act JSON
    eu_ai_act: dict = {}
    if report.eu_ai_act_json:
        try:
            eu_ai_act = json.loads(report.eu_ai_act_json)
        except Exception:
            eu_ai_act = {}

    # Vertex proof from the report record (copied from task at generation time)
    vertex_proof: dict | None = None
    if report.vertex_event_hash:
        vertex_proof = {
            "event_hash": report.vertex_event_hash,
            "round": task.vertex_round,
            "finalised_at": task.vertex_finalised_at.isoformat() if task.vertex_finalised_at else None,
        }

    return {
        "task_id": str(task_id),
        "schema_version": report.schema_version,
        "generated_at": report.generated_at.isoformat() if report.generated_at else None,
        "plain_english_summary": report.narrative or "",
        "eu_ai_act": eu_ai_act,
        "vertex_proof": vertex_proof,
        "report_available": True,
    }


@router.get(
    "/{task_id}/export",
    response_model=dict,
    summary="Export PoC report in structured format",
)
async def export_report(
    task_id: uuid.UUID,
    format: str = Query(default="eu_ai_act", description="Export format (eu_ai_act)"),
    _key_meta: dict = Depends(require_api_key),
    session=Depends(get_db_session),
):
    """
    MT-007: Return the structured compliance export.

    ?format=eu_ai_act returns:
    {
      "task_id": "<uuid>",
      "schema_version": "poc_report_v1",
      "plain_english_summary": "<string>",
      "article_9_risk_management": {...},
      "article_13_transparency": {...},
      "article_17_quality_management": {...},
      "vertex_proof": {...}
    }
    """
    if format != "eu_ai_act":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported export format '{format}'. Supported: eu_ai_act",
        )

    # Verify task exists
    task = await task_repo.get_task(session, task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found.",
        )

    if task.status != "COMPLETED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Task {task_id} is not COMPLETED (status={task.status}).",
        )

    report = await report_repo.get_report_by_task_id(session, task_id)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report for task {task_id} not yet available.",
        )

    eu_ai_act: dict = {}
    if report.eu_ai_act_json:
        try:
            eu_ai_act = json.loads(report.eu_ai_act_json)
        except Exception:
            eu_ai_act = {}

    vertex_proof: dict | None = None
    if report.vertex_event_hash:
        vertex_proof = {
            "event_hash": report.vertex_event_hash,
            "round": task.vertex_round,
            "finalised_at": task.vertex_finalised_at.isoformat() if task.vertex_finalised_at else None,
        }

    # Flat export: top-level article keys + summary + schema metadata
    export = {
        "task_id": str(task_id),
        "schema_version": report.schema_version,
        "plain_english_summary": report.narrative or "",
        "vertex_proof": vertex_proof,
    }
    # Merge EU AI Act article keys at the top level for direct regulatory submission
    export.update(eu_ai_act)

    return export
