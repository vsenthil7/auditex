"""
Auditex -- Claude executor.
Builds the system prompt for a given task_type, calls Claude via claude_service,
parses and validates the structured JSON output, and returns an ExecutorResult.
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


@dataclass
class ExecutorResult:
    output: dict
    confidence: float
    reasoning: str
    model: str
    tokens_used: int


# ---------------------------------------------------------------------------
# System prompts -- CONCISE to avoid hitting max_tokens
# Each prompt instructs Claude to return ONLY a compact JSON object.
# ---------------------------------------------------------------------------
_SYSTEM_PROMPTS: dict[str, str] = {
    "document_review": (
        "You are a financial compliance document reviewer.\n"
        "Respond with ONLY a valid JSON object, no other text:\n"
        "{\n"
        '  "completeness": <float 0.0-1.0>,\n'
        '  "missing_fields": [<string>, ...],\n'
        '  "recommendation": "APPROVE" | "REQUEST_ADDITIONAL_INFO" | "REJECT",\n'
        '  "reasoning": "<2-3 sentence explanation>",\n'
        '  "confidence": <float 0.0-1.0>\n'
        "}"
    ),
    "risk_analysis": (
        "You are a financial risk analyst.\n"
        "Respond with ONLY a valid JSON object, no other text:\n"
        "{\n"
        '  "risk_level": "LOW" | "MEDIUM" | "HIGH",\n'
        '  "risk_factors": [<string>, ...],\n'
        '  "recommendation": "APPROVE" | "REQUEST_ADDITIONAL_INFO" | "REJECT",\n'
        '  "reasoning": "<2-3 sentence explanation>",\n'
        '  "confidence": <float 0.0-1.0>\n'
        "}"
    ),
    "contract_check": (
        "You are a legal contract compliance reviewer.\n"
        "Respond with ONLY a valid JSON object, no other text:\n"
        "{\n"
        '  "compliance_status": "COMPLIANT" | "PARTIAL" | "NON_COMPLIANT",\n'
        '  "issues": [<string>, ...],\n'
        '  "recommendation": "APPROVE" | "REQUEST_AMENDMENTS" | "REJECT",\n'
        '  "reasoning": "<2-3 sentence explanation>",\n'
        '  "confidence": <float 0.0-1.0>\n'
        "}"
    ),
}


def _get_system_prompt(task_type: str) -> str:
    return _SYSTEM_PROMPTS.get(task_type, _SYSTEM_PROMPTS["document_review"])


def _build_user_message(task_type: str, payload: dict) -> str:
    return (
        f"Task type: {task_type}\n\n"
        f"Task payload:\n{json.dumps(payload, indent=2, ensure_ascii=False)}"
    )


def _extract_json(raw_text: str) -> dict:
    text = raw_text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        inner = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
        text = inner.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Claude response is not valid JSON: {exc}\nRaw: {raw_text[:500]}") from exc


async def execute_task(
    task_id: uuid.UUID,
    task_type: str,
    payload: dict,
) -> ExecutorResult:
    system_prompt = _get_system_prompt(task_type)
    user_message = _build_user_message(task_type, payload)
    schema_cls = get_schema_for_task_type(task_type)

    logger.info("Executing task %s type=%s model=%s", task_id, task_type, settings.CLAUDE_MODEL)

    message = await call_claude(
        system_prompt=system_prompt,
        user_message=user_message,
        max_tokens=2048,  # increased from 1024 — risk_analysis/contract_check were truncating
    )

    raw_text = message.content[0].text if message.content else ""

    try:
        raw_dict = _extract_json(raw_text)
    except ValueError as exc:
        logger.error("Task %s: JSON parse failed: %s", task_id, exc)
        raise

    try:
        validated = schema_cls(**raw_dict)
    except ValidationError as exc:
        logger.error("Task %s: schema validation failed type=%s: %s", task_id, task_type, exc)
        raise ValueError(f"Schema validation failed for {task_type}: {exc}") from exc

    validated_dict = validated.model_dump()
    confidence = float(validated_dict.get("confidence", 0.0))
    reasoning = str(validated_dict.get("reasoning", ""))
    tokens_used = message.usage.input_tokens + message.usage.output_tokens

    logger.info("Task %s complete | confidence=%.3f tokens=%d", task_id, confidence, tokens_used)

    return ExecutorResult(
        output=validated_dict,
        confidence=confidence,
        reasoning=reasoning,
        model=message.model,
        tokens_used=tokens_used,
    )
