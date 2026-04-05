"""
Auditex -- GPT-4o reviewer.
Calls the OpenAI API to independently review a Claude executor's output.

Key isolation guarantees (per D-06):
  - The system prompt contains NO reference to Claude or to who produced the output.
  - The user message contains the original task input and the executor output,
    but NOT the executor's identity or reasoning about who produced it.
  - The nonce for the hash commitment is generated fresh per review call.
  - This reviewer is called twice by the coordinator with separate nonces,
    producing two independent verdicts.

This module has NO knowledge of Celery, HTTP, or databases.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from pydantic import BaseModel, Field, ValidationError, field_validator

from services.openai_service import OpenAIServiceError, call_openai

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompt -- used EXACTLY as specified in PHASE-4-BUILD-PROMPT.md
# ---------------------------------------------------------------------------
_GPT4O_REVIEWER_SYSTEM_PROMPT = (
    "You are an independent quality reviewer for an AI compliance platform.\n"
    "You have no knowledge of who produced the output you are reviewing.\n"
    "Assess whether the following AI output is:\n"
    "1. Factually accurate relative to the provided input\n"
    "2. Complete -- does it address all required elements\n"
    "3. Free from hallucination -- does it claim anything not supported by input\n"
    "4. Appropriately calibrated -- is the confidence score justified\n"
    "5. Safe -- does it flag appropriate caveats\n\n"
    'Respond with ONLY a valid JSON object:\n'
    '{\n'
    '  "verdict": "APPROVE" | "REJECT",\n'
    '  "reasoning": "<2-4 sentence explanation>",\n'
    '  "confidence": <float 0.0-1.0>\n'
    '}\n'
    "Do not include any text outside the JSON object."
)


# ---------------------------------------------------------------------------
# Pydantic schema for validating GPT-4o's JSON response
# ---------------------------------------------------------------------------
class _ReviewerResponse(BaseModel):
    verdict: str = Field(..., description="APPROVE or REJECT")
    reasoning: str = Field(..., min_length=1)
    confidence: float = Field(..., ge=0.0, le=1.0)

    @field_validator("verdict")
    @classmethod
    def verdict_must_be_valid(cls, v: str) -> str:
        v = v.upper().strip()
        if v not in ("APPROVE", "REJECT"):
            raise ValueError(f"verdict must be APPROVE or REJECT, got: {v!r}")
        return v


# ---------------------------------------------------------------------------
# Result dataclass returned to the coordinator
# ---------------------------------------------------------------------------
@dataclass
class ReviewVerdict:
    verdict: str          # "APPROVE" or "REJECT"
    reasoning: str        # 2-4 sentence explanation
    confidence: float     # 0.0 - 1.0
    model: str            # actual model name from API response


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
async def review_output(
    *,
    task_type: str,
    original_payload: dict,
    executor_output: dict,
) -> ReviewVerdict:
    """
    Call GPT-4o to independently review the executor's output.

    Args:
        task_type:        The task type (e.g. "document_review") -- context only.
        original_payload: The original task input payload.
        executor_output:  The structured output produced by the Claude executor.
                          NOTE: executor identity is deliberately NOT included.

    Returns:
        ReviewVerdict with verdict, reasoning, confidence, and model name.

    Raises:
        OpenAIServiceError -- if the OpenAI API call fails after all retries.
        ValueError         -- if GPT-4o's response does not match the expected schema.
    """
    # Build user message -- include task context and output, NOT executor identity
    user_message = (
        f"Task type: {task_type}\n\n"
        f"Original task input:\n{json.dumps(original_payload, indent=2, ensure_ascii=False)}\n\n"
        f"AI output to review:\n{json.dumps(executor_output, indent=2, ensure_ascii=False)}"
    )

    logger.info(
        "GPT-4o reviewer: starting review | task_type=%s", task_type
    )

    completion = await call_openai(
        system_prompt=_GPT4O_REVIEWER_SYSTEM_PROMPT,
        user_message=user_message,
        max_tokens=512,
    )

    # Extract text from the first choice
    raw_text = ""
    if completion.choices:
        raw_text = completion.choices[0].message.content or ""

    # Parse and validate the JSON response
    try:
        raw_dict = json.loads(raw_text.strip())
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"GPT-4o reviewer returned non-JSON: {exc}\nRaw: {raw_text[:300]}"
        ) from exc

    try:
        validated = _ReviewerResponse(**raw_dict)
    except ValidationError as exc:
        raise ValueError(
            f"GPT-4o reviewer response failed schema validation: {exc}"
        ) from exc

    logger.info(
        "GPT-4o reviewer: complete | verdict=%s confidence=%.3f model=%s",
        validated.verdict, validated.confidence, completion.model,
    )

    return ReviewVerdict(
        verdict=validated.verdict,
        reasoning=validated.reasoning,
        confidence=validated.confidence,
        model=completion.model,
    )
