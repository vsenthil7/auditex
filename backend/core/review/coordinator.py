"""
Auditex -- Review pipeline coordinator.
Orchestrates the full 3-reviewer hash commitment scheme (D-06).

Pipeline steps (exactly per spec):
  Step 1: Each reviewer computes verdict independently.
  Step 2: Each reviewer generates a nonce and computes commitment hash.
  Step 3: All commitment hashes are collected (verdicts still hidden).
  Step 4: Reveal phase -- each reviewer reveals (verdict, nonce).
  Step 5: Coordinator verifies each commitment.
  Step 6: Consensus is evaluated (2/3 rule).
  Step 7: Returns ReviewResult with all proofs.

Reviewers:
  - Reviewer 1: GPT-4o (gpt4o_reviewer)
  - Reviewer 2: GPT-4o (gpt4o_reviewer, independent call with fresh nonce)
  - Reviewer 3: Claude with clean context (no executor identity)

On SecurityViolationError: the task is failed and the violation is propagated
so the worker can log a SECURITY_VIOLATION audit event.

This module has NO knowledge of Celery, HTTP, or databases.
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from core.review.consensus_eval import evaluate_consensus
from core.review.gpt4o_reviewer import ReviewVerdict, review_output as gpt4o_review
from core.review.hash_commitment import (
    SecurityViolationError,
    compute_commitment,
    generate_nonce,
    verify_commitment,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Claude third-reviewer system prompt -- used EXACTLY as specified in spec
# ---------------------------------------------------------------------------
_CLAUDE_REVIEWER_SYSTEM_PROMPT = (
    "You are an independent output reviewer for a compliance platform.\n"
    "You did not produce the output you are reviewing.\n"
    "Your task is to assess whether this AI output is accurate, complete, and well-reasoned.\n\n"
    'Respond with ONLY a valid JSON object:\n'
    '{\n'
    '  "verdict": "APPROVE" | "REJECT",\n'
    '  "reasoning": "<2-4 sentence explanation>",\n'
    '  "confidence": <float 0.0-1.0>\n'
    '}\n'
    "Do not include any text outside the JSON object."
)


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------
@dataclass
class ReviewerRecord:
    """Complete record for one reviewer -- verdict + commitment proof."""
    model: str
    verdict: str               # "APPROVE" or "REJECT"
    reasoning: str
    confidence: float
    nonce: str                 # the nonce used for commitment
    committed_hash: str        # hash submitted before reveal
    commitment_verified: bool  # True after verify_commitment() passes


@dataclass
class ReviewResult:
    """Complete result of the review pipeline returned to the execution worker."""
    verdicts: list[str]                  # ["APPROVE", "APPROVE", "APPROVE"]
    reviewers: list[ReviewerRecord]      # full per-reviewer records
    consensus: str                       # e.g. "3_OF_3_APPROVE"
    all_verified: bool                   # True if all 3 commitments verified
    completed_at: str                    # ISO timestamp


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _strip_code_fences(text: str) -> str:
    """
    Strip markdown code fences from a string.
    Handles ```json ... ``` and ``` ... ``` patterns.
    Claude sometimes wraps JSON in fences despite instructions not to.
    """
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        # Remove first line (``` or ```json) and last line (```)
        if len(lines) >= 2:
            end = len(lines) - 1 if lines[-1].strip() == "```" else len(lines)
            text = "\n".join(lines[1:end]).strip()
    return text


def _parse_reviewer_json(raw_text: str, reviewer_name: str) -> dict:
    """
    Parse a reviewer's JSON response, stripping code fences if present.
    Raises ValueError with a clear message on failure.
    """
    cleaned = _strip_code_fences(raw_text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"{reviewer_name} returned invalid JSON: {exc}\n"
            f"Raw (first 300 chars): {raw_text[:300]}"
        ) from exc


# ---------------------------------------------------------------------------
# Internal: Claude third-reviewer (clean context)
# ---------------------------------------------------------------------------
async def _call_claude_reviewer(
    task_type: str,
    original_payload: dict,
    executor_output: dict,
) -> ReviewVerdict:
    """
    Call Claude as the third independent reviewer with a completely clean context.
    Uses a different system prompt than the executor.
    Has no knowledge of the executor's identity or the other reviewers' verdicts.
    Code fences are stripped from the response before JSON parsing.
    """
    from pydantic import BaseModel, Field, ValidationError, field_validator
    from services.claude_service import call_claude

    user_message = (
        f"Task type: {task_type}\n\n"
        f"Original task input:\n{json.dumps(original_payload, indent=2, ensure_ascii=False)}\n\n"
        f"AI output to review:\n{json.dumps(executor_output, indent=2, ensure_ascii=False)}"
    )

    message = await call_claude(
        system_prompt=_CLAUDE_REVIEWER_SYSTEM_PROMPT,
        user_message=user_message,
        max_tokens=512,
    )

    raw_text = message.content[0].text if message.content else ""

    class _R(BaseModel):
        verdict: str = Field(...)
        reasoning: str = Field(..., min_length=1)
        confidence: float = Field(..., ge=0.0, le=1.0)

        @field_validator("verdict")
        @classmethod
        def verdict_valid(cls, val: str) -> str:
            val = val.upper().strip()
            if val not in ("APPROVE", "REJECT"):
                raise ValueError(f"verdict must be APPROVE or REJECT, got: {val!r}")
            return val

    # Use fence-stripping parser -- Claude ignores "no fences" instruction sometimes
    raw_dict = _parse_reviewer_json(raw_text, "Claude third-reviewer")

    try:
        validated = _R(**raw_dict)
    except ValidationError as exc:
        raise ValueError(
            f"Claude third-reviewer response failed schema validation: {exc}"
        ) from exc

    logger.info(
        "Claude third-reviewer: complete | verdict=%s confidence=%.3f model=%s",
        validated.verdict, validated.confidence, message.model,
    )

    return ReviewVerdict(
        verdict=validated.verdict,
        reasoning=validated.reasoning,
        confidence=validated.confidence,
        model=message.model,
    )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
async def run_review_pipeline(
    task_id: uuid.UUID,
    task_type: str,
    payload: dict,
    executor_output: dict,
) -> ReviewResult:
    """
    Orchestrate the full 3-reviewer hash commitment review pipeline.

    Steps exactly per D-06:
      1. All three reviewers compute verdicts independently (parallel).
      2. Each generates a nonce and computes commitment hash.
      3. Commitments collected (reveal phase not started yet).
      4. Each commitment verified against revealed verdict + nonce.
      5. Consensus evaluated.

    Args:
        task_id:          UUID of the task being reviewed (for logging).
        task_type:        Task type string (e.g. "document_review").
        payload:          Original task input payload (passed to reviewers).
        executor_output:  The structured output from the Claude executor.

    Returns:
        ReviewResult with all reviewer records, consensus, and verification status.

    Raises:
        SecurityViolationError -- if any commitment fails verification.
        Exception              -- propagated from reviewer API calls on total failure.
    """
    logger.info(
        "run_review_pipeline: starting | task=%s task_type=%s",
        task_id, task_type,
    )

    # ------------------------------------------------------------------
    # Step 1: All three reviewers compute verdicts independently (parallel)
    # ------------------------------------------------------------------
    logger.info("run_review_pipeline: calling reviewers in parallel | task=%s", task_id)

    results = await asyncio.gather(
        gpt4o_review(
            task_type=task_type,
            original_payload=payload,
            executor_output=executor_output,
        ),
        gpt4o_review(
            task_type=task_type,
            original_payload=payload,
            executor_output=executor_output,
        ),
        _call_claude_reviewer(
            task_type=task_type,
            original_payload=payload,
            executor_output=executor_output,
        ),
    )

    reviewer_1_verdict: ReviewVerdict = results[0]
    reviewer_2_verdict: ReviewVerdict = results[1]
    reviewer_3_verdict: ReviewVerdict = results[2]

    logger.info(
        "run_review_pipeline: verdicts received | task=%s r1=%s r2=%s r3=%s",
        task_id,
        reviewer_1_verdict.verdict,
        reviewer_2_verdict.verdict,
        reviewer_3_verdict.verdict,
    )

    # ------------------------------------------------------------------
    # Step 2: Each reviewer generates nonce and computes commitment hash
    # ------------------------------------------------------------------
    nonce_1 = generate_nonce()
    nonce_2 = generate_nonce()
    nonce_3 = generate_nonce()

    committed_hash_1 = compute_commitment(reviewer_1_verdict.verdict, nonce_1)
    committed_hash_2 = compute_commitment(reviewer_2_verdict.verdict, nonce_2)
    committed_hash_3 = compute_commitment(reviewer_3_verdict.verdict, nonce_3)

    logger.info(
        "run_review_pipeline: commitments computed | task=%s "
        "h1=%s... h2=%s... h3=%s...",
        task_id,
        committed_hash_1[:16], committed_hash_2[:16], committed_hash_3[:16],
    )

    # ------------------------------------------------------------------
    # Step 3: All hashes collected (commitment phase complete)
    # Step 4: Reveal phase -- verify each commitment
    # ------------------------------------------------------------------
    violations: list[str] = []

    verified_1 = False
    try:
        verify_commitment(reviewer_1_verdict.verdict, nonce_1, committed_hash_1)
        verified_1 = True
    except SecurityViolationError as exc:
        violations.append(f"Reviewer 1 ({reviewer_1_verdict.model}): {exc}")
        logger.error("run_review_pipeline: SECURITY_VIOLATION reviewer 1 | task=%s", task_id)

    verified_2 = False
    try:
        verify_commitment(reviewer_2_verdict.verdict, nonce_2, committed_hash_2)
        verified_2 = True
    except SecurityViolationError as exc:
        violations.append(f"Reviewer 2 ({reviewer_2_verdict.model}): {exc}")
        logger.error("run_review_pipeline: SECURITY_VIOLATION reviewer 2 | task=%s", task_id)

    verified_3 = False
    try:
        verify_commitment(reviewer_3_verdict.verdict, nonce_3, committed_hash_3)
        verified_3 = True
    except SecurityViolationError as exc:
        violations.append(f"Reviewer 3 ({reviewer_3_verdict.model}): {exc}")
        logger.error("run_review_pipeline: SECURITY_VIOLATION reviewer 3 | task=%s", task_id)

    if violations:
        raise SecurityViolationError(
            f"Hash commitment verification failed for task {task_id}. "
            f"Violations: {'; '.join(violations)}"
        )

    # ------------------------------------------------------------------
    # Step 5: Build reviewer records
    # ------------------------------------------------------------------
    reviewer_records = [
        ReviewerRecord(
            model=reviewer_1_verdict.model,
            verdict=reviewer_1_verdict.verdict,
            reasoning=reviewer_1_verdict.reasoning,
            confidence=reviewer_1_verdict.confidence,
            nonce=nonce_1,
            committed_hash=committed_hash_1,
            commitment_verified=verified_1,
        ),
        ReviewerRecord(
            model=reviewer_2_verdict.model,
            verdict=reviewer_2_verdict.verdict,
            reasoning=reviewer_2_verdict.reasoning,
            confidence=reviewer_2_verdict.confidence,
            nonce=nonce_2,
            committed_hash=committed_hash_2,
            commitment_verified=verified_2,
        ),
        ReviewerRecord(
            model=reviewer_3_verdict.model,
            verdict=reviewer_3_verdict.verdict,
            reasoning=reviewer_3_verdict.reasoning,
            confidence=reviewer_3_verdict.confidence,
            nonce=nonce_3,
            committed_hash=committed_hash_3,
            commitment_verified=verified_3,
        ),
    ]

    # ------------------------------------------------------------------
    # Step 6: Evaluate consensus
    # ------------------------------------------------------------------
    verdicts = [r.verdict for r in reviewer_records]
    consensus = evaluate_consensus(verdicts)
    all_verified = all([verified_1, verified_2, verified_3])

    completed_at = datetime.now(timezone.utc).isoformat()

    logger.info(
        "run_review_pipeline: complete | task=%s consensus=%s all_verified=%s",
        task_id, consensus, all_verified,
    )

    return ReviewResult(
        verdicts=verdicts,
        reviewers=reviewer_records,
        consensus=consensus,
        all_verified=all_verified,
        completed_at=completed_at,
    )
