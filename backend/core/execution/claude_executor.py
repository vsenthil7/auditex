"""
Auditex -- Claude executor.
Builds the system prompt for a given task_type, calls Claude via claude_service,
parses and validates the structured JSON output, and returns an ExecutorResult.

This module has NO knowledge of Celery, HTTP, or databases.
It is a pure function: task_type + payload -> ExecutorResult.
"""
from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass

from pydantic import ValidationError

from app.config import settings
from core.execution.task_schemas import get_schema_for_task_type
from services.claude_service import ClaudeServiceError, call_claude

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result dataclass returned to the execution worker
# ---------------------------------------------------------------------------
@dataclass
class ExecutorResult:
    output: dict          # Validated structured output (task-specific schema)
    confidence: float     # 0.0 - 1.0
    reasoning: str        # Extracted from output or synthetic
    model: str            # Model name actually used (from API response)
    tokens_used: int      # Total tokens (input + output)


# ---------------------------------------------------------------------------
# System prompts -- keyed by task_type
# Used exactly as specified in PHASE-3-BUILD-PROMPT.md
# ---------------------------------------------------------------------------
_SYSTEM_PROMPTS: dict[str, str] = {
    "document_review": (
        "You are an expert document review specialist for a financial compliance team.\n"
        "You are reviewing a document for completeness and accuracy.\n"
        "You must respond with ONLY a valid JSON object matching this exact schema:\n"
        "{\n"
        '  "completeness": <float 0.0-1.0>,\n'
        '  "missing_fields": [<string>, ...],\n'
        '  "recommendation": "APPROVE" | "REQUEST_ADDITIONAL_INFO" | "REJECT",\n'
        '  "reasoning": "<2-3 sentence explanation>",\n'
        '  "confidence": <float 0.0-1.0>\n'
        "}\n"
        "Do not include any text outside the JSON object."
    ),
}

_GENERIC_SYSTEM_PROMPT = (
    "You are an AI task execution specialist for a compliance platform.\n"
    "Complete the following task and respond with ONLY a valid JSON object:\n"
    "{\n"
    '  "result": "<your output>",\n'
    '  "reasoning": "<2-3 sentence explanation>",\n'
    '  "confidence": <float 0.0-1.0>\n'
    "}\n"
    "Do not include any text outside the JSON object."
)


def _get_system_prompt(task_type: str) -> str:
    return _SYSTEM_PROMPTS.get(task_type, _GENERIC_SYSTEM_PROMPT)


def _build_user_message(task_type: str, payload: dict) -> str:
    """Serialise the task payload as the user message."""
    return (
        f"Task type: {task_type}\n\n"
        f"Task payload:\n{json.dumps(payload, indent=2, ensure_ascii=False)}"
    )


def _extract_json(raw_text: str) -> dict:
    """
    Extract a JSON object from Claude's response text.
    Strips markdown code fences if present, then parses.
    Raises ValueError if no valid JSON is found.
    """
    text = raw_text.strip()

    # Strip ```json ... ``` or ``` ... ``` fences
    if text.startswith("```"):
        lines = text.splitlines()
        # Remove first line (``` or ```json) and last line (```)
        inner = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
        text = inner.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Claude response is not valid JSON: {exc}\nRaw: {raw_text[:300]}") from exc


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
async def execute_task(
    task_id: uuid.UUID,
    task_type: str,
    payload: dict,
) -> ExecutorResult:
    """
    Execute a task using Claude and return a validated ExecutorResult.

    Args:
        task_id:   UUID of the task (used for logging only).
        task_type: Task type string (e.g. "document_review").
        payload:   Task payload dict from the database.

    Returns:
        ExecutorResult with validated structured output.

    Raises:
        ClaudeServiceError -- if Claude API fails after all retries.
        ValueError         -- if Claude's output does not match the expected schema.
    """
    system_prompt = _get_system_prompt(task_type)
    user_message = _build_user_message(task_type, payload)
    schema_cls = get_schema_for_task_type(task_type)

    logger.info(
        "Executing task %s type=%s model=%s",
        task_id, task_type, settings.CLAUDE_MODEL,
    )

    # Call Claude via the service layer (handles retries + timeout)
    message = await call_claude(
        system_prompt=system_prompt,
        user_message=user_message,
        max_tokens=1024,
    )

    # Extract the text content from the response
    raw_text = message.content[0].text if message.content else ""

    # Parse JSON
    try:
        raw_dict = _extract_json(raw_text)
    except ValueError as exc:
        logger.error("Task %s: JSON parse failed: %s", task_id, exc)
        raise

    # Validate against the task-specific Pydantic schema
    try:
        validated = schema_cls(**raw_dict)
    except ValidationError as exc:
        logger.error(
            "Task %s: schema validation failed for type=%s: %s",
            task_id, task_type, exc,
        )
        raise ValueError(
            f"Claude output failed schema validation for task_type={task_type}: {exc}"
        ) from exc

    validated_dict = validated.model_dump()
    confidence = float(validated_dict.get("confidence", 0.0))
    reasoning = str(validated_dict.get("reasoning", ""))

    tokens_used = message.usage.input_tokens + message.usage.output_tokens

    logger.info(
        "Task %s execution complete | confidence=%.3f tokens=%d",
        task_id, confidence, tokens_used,
    )

    return ExecutorResult(
        output=validated_dict,
        confidence=confidence,
        reasoning=reasoning,
        model=message.model,
        tokens_used=tokens_used,
    )
