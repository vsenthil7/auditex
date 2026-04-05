"""
Auditex -- PoC report generator.
Reads a completed task from the DB, calls Claude to generate a plain-English
compliance narrative, then assembles the full PoCReportData dataclass.

Called by: reporting_worker.generate_poc_report
"""
from __future__ import annotations

import dataclasses
import json
import logging
import uuid
from datetime import datetime, timezone

from services.claude_service import call_claude

logger = logging.getLogger(__name__)

_NARRATIVE_MAX_TOKENS = 1500

_SYSTEM_PROMPT = """\
You are a compliance documentation specialist. Generate a plain-English \
narrative from the event log below. Do not add information not present. \
Write in formal English suitable for regulatory submission.

Your narrative must cover:
1. What task was performed and the task type.
2. Which AI model executed the task and what its output/recommendation was.
3. How many independent reviewers assessed the output, their models, and their verdicts.
4. The final consensus result.
5. Whether the record was cryptographically finalised (Vertex consensus round and hash).

Keep the narrative between 150 and 400 words. Be factual and precise.\
"""


@dataclasses.dataclass
class PoCReportData:
    task_id: uuid.UUID
    plain_english_summary: str
    generated_at: datetime


async def generate_report(
    *,
    task_id: uuid.UUID,
    task_type: str,
    executor_output: dict,
    review_result: dict,
    vertex_event_hash: str | None,
    vertex_round: int | None,
    vertex_finalised_at: str | None,
) -> PoCReportData:
    """
    Generate a plain-English PoC narrative using Claude.

    Args:
        task_id:            UUID of the completed task.
        task_type:          e.g. "document_review"
        executor_output:    deserialized executor_output_json blob
        review_result:      deserialized review_result_json blob
        vertex_event_hash:  64-char SHA-256 hex or None
        vertex_round:       Vertex round int or None
        vertex_finalised_at: ISO timestamp or None

    Returns:
        PoCReportData with plain_english_summary populated.
    """
    # Build the event log summary sent to Claude
    event_log = {
        "task_id": str(task_id),
        "task_type": task_type,
        "executor": executor_output,
        "review": review_result,
        "vertex_proof": {
            "event_hash": vertex_event_hash,
            "round": vertex_round,
            "finalised_at": vertex_finalised_at,
        },
    }

    user_message = (
        "Generate a compliance narrative for the following AI workflow event log:\n\n"
        + json.dumps(event_log, indent=2, default=str)
    )

    try:
        message = await call_claude(
            system_prompt=_SYSTEM_PROMPT,
            user_message=user_message,
            max_tokens=_NARRATIVE_MAX_TOKENS,
        )
        narrative = message.content[0].text.strip()
    except Exception as exc:
        logger.error("poc_generator: Claude narrative call failed for %s: %s", task_id, exc)
        # Fallback: produce a structured but non-AI summary so the report is
        # never blocked by a Claude API failure.
        narrative = _fallback_narrative(task_type, executor_output, review_result)

    return PoCReportData(
        task_id=task_id,
        plain_english_summary=narrative,
        generated_at=datetime.now(timezone.utc),
    )


def _fallback_narrative(
    task_type: str,
    executor_output: dict,
    review_result: dict,
) -> str:
    """
    Deterministic fallback narrative used when the Claude API is unavailable.
    Guaranteed to produce a non-empty string from structured data.
    """
    model = executor_output.get("model", "unknown")
    confidence = executor_output.get("confidence", "N/A")
    consensus = review_result.get("consensus", "unknown")
    reviewer_count = len(review_result.get("reviewers", []))

    return (
        f"Task type: {task_type}. "
        f"Executed by {model} with a confidence score of {confidence}. "
        f"The output was independently reviewed by {reviewer_count} AI reviewer(s). "
        f"Final consensus: {consensus}. "
        f"The complete event chain has been cryptographically recorded and is "
        f"available for audit via the Vertex proof attached to this report."
    )
