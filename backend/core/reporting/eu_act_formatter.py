"""
Auditex -- EU AI Act formatter.
Maps completed task data to the EU AI Act Article 9 / 13 / 17 structure.

Article 9  -- Risk management: what was done, by whom, with what confidence
Article 13 -- Transparency: what decision was made and who reviewed it
Article 17 -- Quality management: tamper-proof proof chain

Called by: reporting_worker.generate_poc_report
"""
from __future__ import annotations

import json
import logging

logger = logging.getLogger(__name__)

# Risk thresholds -- confidence score to risk band mapping
_RISK_HIGH_THRESHOLD = 0.60
_RISK_MEDIUM_THRESHOLD = 0.80


def _confidence_to_risk(confidence: float | None) -> str:
    """Map executor confidence to a regulatory risk band."""
    if confidence is None:
        return "UNKNOWN"
    if confidence < _RISK_HIGH_THRESHOLD:
        return "HIGH"
    if confidence < _RISK_MEDIUM_THRESHOLD:
        return "MEDIUM"
    return "LOW"


def format_eu_ai_act(
    *,
    task_type: str,
    executor_output: dict,
    review_result: dict,
    vertex_event_hash: str | None,
    vertex_round: int | None,
    vertex_finalised_at: str | None,
) -> dict:
    """
    Build the EU AI Act structured export object.

    Args:
        task_type:           e.g. "document_review"
        executor_output:     deserialized executor_output_json blob
                             {model, output, confidence, completed_at}
        review_result:       deserialized review_result_json blob
                             {consensus, reviewers: [{model, verdict, confidence, ...}],
                              completed_at}
        vertex_event_hash:   64-char SHA-256 hex or None
        vertex_round:        Vertex consensus round int or None
        vertex_finalised_at: ISO timestamp string or None

    Returns:
        dict matching the MT-007 eu_ai_act schema.
    """
    executor_model = executor_output.get("model", "unknown")
    confidence = executor_output.get("confidence")
    if confidence is not None:
        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            confidence = None

    # Extract decision from executor output (nested under "output" key)
    raw_output = executor_output.get("output", {})
    if isinstance(raw_output, str):
        try:
            raw_output = json.loads(raw_output)
        except Exception:
            raw_output = {}

    recommendation = raw_output.get("recommendation", "")
    reasoning = raw_output.get("reasoning", "")
    if not reasoning:
        reasoning = raw_output.get("summary", "")
    if not reasoning and isinstance(raw_output, dict):
        # Fallback: join any string values
        reasoning = "; ".join(
            str(v) for v in raw_output.values() if isinstance(v, str) and v
        )[:500]

    # Review reviewer list
    reviewers_raw = review_result.get("reviewers", [])
    reviewers = [
        {
            "model": r.get("model", "unknown"),
            "verdict": r.get("verdict", "UNKNOWN"),
            "confidence": float(r.get("confidence", 0.0)),
        }
        for r in reviewers_raw
    ]

    consensus = review_result.get("consensus", "UNKNOWN")
    all_commitments_verified = all(
        r.get("commitment_verified", False) for r in reviewers_raw
    )

    return {
        "article_9_risk_management": {
            "task_type": task_type,
            "executor_model": executor_model,
            "confidence_score": confidence,
            "risk_assessment": _confidence_to_risk(confidence),
        },
        "article_13_transparency": {
            "decision_made": recommendation,
            "reasoning_summary": reasoning[:500] if reasoning else "",
            "reviewers": reviewers,
            "consensus": consensus,
        },
        "article_17_quality_management": {
            "all_commitments_verified": all_commitments_verified,
            "vertex_event_hash": vertex_event_hash or "",
            "vertex_round": vertex_round,
            "finalised_at": vertex_finalised_at or "",
            "audit_trail_available": True,
        },
    }
