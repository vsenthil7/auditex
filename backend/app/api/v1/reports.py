"""
Auditex -- Reports routes (Phase 6, extended by Phase 11 Item 1b).

GET /api/v1/reports/{task_id}
    Returns the full PoC report for a completed task.
    Includes: plain_english_summary, eu_ai_act, vertex_proof,
              schema_version, generated_at, report_available,
              signature (if present).

GET /api/v1/reports/{task_id}/export?format=eu_ai_act
    Returns the structured EU AI Act export dict plus summary and vertex proof.

GET /api/v1/reports/{task_id}/export?format=eu_ai_act&signed=true
    Same as above, but wraps the payload in a signed envelope:
        {
          "schema": "auditex_signed_export_v1",
          "payload": <the normal export dict>,
          "signature": {algorithm, signing_key_id, signed_at, signature_hex}
        }
    The signature is ALWAYS computed fresh from the current payload, so
    reordering or re-serialising the payload does not invalidate it.
    If the report has a stored signature from a previous POST /sign call,
    it is returned as `stored_signature` alongside the fresh envelope for
    cross-checking.

POST /api/v1/reports/{task_id}/sign
    Signs the current EU AI Act export payload and PERSISTS the signature
    onto the Report (org_signature, signing_key_id, signed_at).
    Returns the signed envelope. Idempotent: re-signing overwrites the
    stored signature with a fresh one (signatures are not append-only
    because the ACTIVE key may rotate).

All routes require X-API-Key authentication.
"""
from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.middleware.auth import require_api_key
from core.reporting import export_signer
from db.connection import get_db_session
from db.repositories import report_repo, task_repo

router = APIRouter(prefix="/reports", tags=["reports"])


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _parse_eu_ai_act(report) -> dict:
    """Deserialise eu_ai_act_json safely. Returns {} on missing or bad JSON."""
    if not report.eu_ai_act_json:
        return {}
    try:
        return json.loads(report.eu_ai_act_json)
    except Exception:
        return {}


def _vertex_proof_from(task, report) -> dict | None:
    """Build the vertex_proof dict from task + report, or None if no hash."""
    if not report.vertex_event_hash:
        return None
    finalised = (
        task.vertex_finalised_at.isoformat()
        if task.vertex_finalised_at else None
    )
    return {
        "event_hash": report.vertex_event_hash,
        "round": task.vertex_round,
        "finalised_at": finalised,
    }


def _stored_signature_of(report) -> dict | None:
    """
    Return the persisted signature envelope fragment if the Report was signed,
    else None. Keys match export_signer.sign_export()['signature'] shape.
    """
    if not getattr(report, "org_signature", None):
        return None
    signed_at = getattr(report, "signed_at", None)
    signed_at_iso = signed_at.isoformat() if signed_at else None
    return {
        "algorithm": export_signer.ALGORITHM,
        "signing_key_id": getattr(report, "signing_key_id", None),
        "signed_at": signed_at_iso,
        "signature_hex": report.org_signature,
    }


async def _load_completed_report(task_id: uuid.UUID, session):
    """
    Common guard: 404 if task missing, 400 if not COMPLETED, 404 if report
    not yet generated. Returns (task, report) on success.
    """
    task = await task_repo.get_task(session, task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found.",
        )
    if task.status != "COMPLETED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Task {task_id} is not COMPLETED (status={task.status})."
            ),
        )
    report = await report_repo.get_report_by_task_id(session, task_id)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report for task {task_id} not yet available.",
        )
    return task, report


def _build_export_payload(task, report) -> dict:
    """
    Build the flat EU AI Act export dict (schema_version + summary + vertex
    + article_* keys merged at top level).
    """
    eu_ai_act = _parse_eu_ai_act(report)
    payload = {
        "task_id": str(task.id),
        "schema_version": report.schema_version,
        "plain_english_summary": report.narrative or "",
        "vertex_proof": _vertex_proof_from(task, report),
    }
    payload.update(eu_ai_act)
    return payload


# --------------------------------------------------------------------------- #
# GET /reports/{task_id}
# --------------------------------------------------------------------------- #
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
      "eu_ai_act": {...},
      "vertex_proof": {...} | null,
      "report_available": true,
      "signature": {...} | null   # only present if POST /sign was called
    }
    """
    task, report = await _load_completed_report(task_id, session)

    return {
        "task_id": str(task_id),
        "schema_version": report.schema_version,
        "generated_at": report.generated_at.isoformat() if report.generated_at else None,
        "plain_english_summary": report.narrative or "",
        "eu_ai_act": _parse_eu_ai_act(report),
        "vertex_proof": _vertex_proof_from(task, report),
        "report_available": True,
        "signature": _stored_signature_of(report),
    }


# --------------------------------------------------------------------------- #
# GET /reports/{task_id}/export
# --------------------------------------------------------------------------- #
@router.get(
    "/{task_id}/export",
    response_model=dict,
    summary="Export PoC report in structured format",
)
async def export_report(
    task_id: uuid.UUID,
    format: str = Query(default="eu_ai_act", description="Export format (eu_ai_act)"),
    signed: bool = Query(default=False, description="Wrap response in signed envelope"),
    _key_meta: dict = Depends(require_api_key),
    session=Depends(get_db_session),
):
    """
    MT-007: Return the structured compliance export.

    Unsigned (default, backward-compatible):
      Returns the flat export dict directly.

    Signed (?signed=true):
      Returns an envelope:
        {
          "schema": "auditex_signed_export_v1",
          "payload": <flat export dict>,
          "signature": {algorithm, signing_key_id, signed_at, signature_hex},
          "stored_signature": {...} | null
        }
      ``stored_signature`` echoes the persisted signature (if any) so clients
      can detect key rotation without a second request.
    """
    if format != "eu_ai_act":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported export format '{format}'. Supported: eu_ai_act",
        )

    task, report = await _load_completed_report(task_id, session)
    payload = _build_export_payload(task, report)

    if not signed:
        return payload

    try:
        envelope = export_signer.sign_export(payload)
    except export_signer.SigningKeyNotConfigured as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Export signing unavailable: {exc}",
        )

    envelope["stored_signature"] = _stored_signature_of(report)
    return envelope


# --------------------------------------------------------------------------- #
# POST /reports/{task_id}/sign
# --------------------------------------------------------------------------- #
@router.post(
    "/{task_id}/sign",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Sign and persist the EU AI Act export for a completed task",
)
async def sign_report_endpoint(
    task_id: uuid.UUID,
    _key_meta: dict = Depends(require_api_key),
    session=Depends(get_db_session),
):
    """
    Phase 11 Item 1b.2: Produce a signed EU AI Act export envelope AND persist
    the signature on the Report record.

    Returns the same envelope shape as GET /export?signed=true, plus
    ``persisted: true``.
    """
    task, report = await _load_completed_report(task_id, session)
    payload = _build_export_payload(task, report)

    try:
        envelope = export_signer.sign_export(payload)
    except export_signer.SigningKeyNotConfigured as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Export signing unavailable: {exc}",
        )

    # Persist signature onto the Report row.
    await report_repo.sign_report(
        session,
        task_id,
        signature_hex=envelope["signature"]["signature_hex"],
        signing_key_id=envelope["signature"]["signing_key_id"],
    )
    await session.commit()

    envelope["persisted"] = True
    return envelope
