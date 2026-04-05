"""
Auditex -- Consensus event builder.
Constructs the canonical FoxMQ/Vertex event payload for a completed task.

This module is infrastructure-agnostic: it builds the payload dict that is then
handed to foxmq_client.publish_event() and vertex_client.submit_event().
No network I/O happens here.

Phase 5: Production-ready event schema, designed for real Vertex/FoxMQ
         once infrastructure is available (Phase 6+).
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any


def _sha256_of_json(obj: Any) -> str:
    """
    Compute SHA-256 of a JSON-serialised object.
    Keys are sorted for determinism. Returns lowercase hex string.
    """
    serialised = json.dumps(obj, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialised.encode("utf-8")).hexdigest()


def build_task_completed_event(
    task_id: str,
    task_type: str,
    executor_output: dict,
    review_result: Any,
) -> dict:
    """
    Build the canonical FoxMQ/Vertex event payload for a completed task.

    Args:
        task_id:        UUID string of the task.
        task_type:      e.g. "document_review".
        executor_output: The raw output dict from the Claude executor
                         (the "output" field, not the full blob).
        review_result:  ReviewPipelineResult dataclass from coordinator.

    Returns:
        A dict representing the full event payload.
        The caller (vertex_client) will compute the final event_hash
        from this payload.

    Event schema v1.0:
    {
      "event_type": "task_completed",
      "task_id": "<uuid>",
      "schema_version": "1.0",
      "executor": {
        "model": "<model>",
        "output_hash": "<sha256 of json-serialised executor output>",
        "confidence": <float>
      },
      "reviewers": [
        {"model": "<model>", "verdict": "<verdict>", "committed_hash": "<hash>"},
        ...
      ],
      "consensus": "<consensus_label>",
      "all_commitments_verified": <bool>,
      "submitted_at": "<ISO timestamp>"
    }
    """
    # Hash the raw executor output for tamper-evidence
    output_hash = _sha256_of_json(executor_output)

    # Extract executor model and confidence from the review_result context
    # review_result.reviewers[2] is the Claude reviewer (index 2, clean context)
    # The executor model is stored separately on executor_output if available,
    # otherwise we default to the known executor model.
    executor_model = "claude-sonnet-4-6"  # canonical executor for Phase 5

    # Attempt to read confidence from review_result if accessible
    executor_confidence: float | None = None
    try:
        executor_confidence = float(review_result.executor_confidence)
    except (AttributeError, TypeError, ValueError):
        executor_confidence = None

    # Build reviewer entries from review_result
    reviewers = []
    try:
        for r in review_result.reviewers:
            entry: dict = {
                "model": r.model,
                "verdict": r.verdict,
                "committed_hash": getattr(r, "committed_hash", None),
            }
            reviewers.append(entry)
    except (AttributeError, TypeError):
        reviewers = []

    submitted_at = datetime.now(timezone.utc).isoformat()

    payload: dict = {
        "event_type": "task_completed",
        "task_id": str(task_id),
        "schema_version": "1.0",
        "executor": {
            "model": executor_model,
            "output_hash": output_hash,
            "confidence": executor_confidence,
        },
        "reviewers": reviewers,
        "consensus": review_result.consensus,
        "all_commitments_verified": review_result.all_verified,
        "submitted_at": submitted_at,
    }

    return payload
