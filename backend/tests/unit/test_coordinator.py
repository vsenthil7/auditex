"""Tests for core.review.coordinator."""
from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.review import coordinator
from core.review.coordinator import (
    ReviewResult,
    ReviewerRecord,
    _call_claude_reviewer,
    _parse_reviewer_json,
    _strip_code_fences,
    run_review_pipeline,
)
from core.review.gpt4o_reviewer import ReviewVerdict


def test_strip_code_fences_plain():
    assert _strip_code_fences('{"a": 1}') == '{"a": 1}'


def test_strip_code_fences_json_fence():
    raw = '```json\n{"a": 1}\n```'
    assert _strip_code_fences(raw) == '{"a": 1}'


def test_strip_code_fences_plain_fence():
    raw = '```\n{"a": 2}\n```'
    assert _strip_code_fences(raw) == '{"a": 2}'


def test_strip_code_fences_unclosed():
    raw = '```\n{"a": 3}'
    assert _strip_code_fences(raw) == '{"a": 3}'


def test_parse_reviewer_json_valid():
    assert _parse_reviewer_json('{"a": 1}', "r") == {"a": 1}


def test_parse_reviewer_json_with_fence():
    assert _parse_reviewer_json('```json\n{"a": 2}\n```', "r") == {"a": 2}


def test_parse_reviewer_json_invalid_raises():
    with pytest.raises(ValueError):
        _parse_reviewer_json("not json", "r1")


def _make_claude_message(content_str: str, model="claude-sonnet-4-6"):
    m = MagicMock()
    m.content = [MagicMock(text=content_str)]
    m.model = model
    return m


@pytest.mark.asyncio
async def test_call_claude_reviewer_success():
    msg = _make_claude_message(json.dumps({
        "verdict": "APPROVE", "reasoning": "x", "confidence": 0.9,
    }))
    with patch("services.claude_service.call_claude", AsyncMock(return_value=msg)):
        v = await _call_claude_reviewer(
            task_type="document_review", original_payload={}, executor_output={},
        )
    assert v.verdict == "APPROVE"


@pytest.mark.asyncio
async def test_call_claude_reviewer_bad_verdict_raises():
    msg = _make_claude_message(json.dumps({
        "verdict": "MAYBE", "reasoning": "x", "confidence": 0.9,
    }))
    with patch("services.claude_service.call_claude", AsyncMock(return_value=msg)):
        with pytest.raises(ValueError):
            await _call_claude_reviewer(
                task_type="document_review", original_payload={}, executor_output={},
            )


@pytest.mark.asyncio
async def test_call_claude_reviewer_empty_content():
    msg = MagicMock()
    msg.content = []
    msg.model = "claude"
    with patch("services.claude_service.call_claude", AsyncMock(return_value=msg)):
        with pytest.raises(ValueError):
            await _call_claude_reviewer(
                task_type="document_review", original_payload={}, executor_output={},
            )


def _mock_verdict(v="APPROVE", model="gpt-4o"):
    return ReviewVerdict(verdict=v, reasoning="r", confidence=0.9, model=model)


@pytest.mark.asyncio
async def test_run_review_pipeline_all_approve():
    r1 = _mock_verdict("APPROVE", "gpt-4o")
    r2 = _mock_verdict("APPROVE", "gpt-4o")
    r3 = _mock_verdict("APPROVE", "claude")
    with patch.object(coordinator, "gpt4o_review", AsyncMock(side_effect=[r1, r2])), \
         patch.object(coordinator, "_call_claude_reviewer", AsyncMock(return_value=r3)):
        result = await run_review_pipeline(
            task_id=uuid.uuid4(), task_type="document_review",
            payload={}, executor_output={},
        )
    assert isinstance(result, ReviewResult)
    assert result.consensus == "3_OF_3_APPROVE"
    assert result.all_verified is True
    assert len(result.reviewers) == 3
    for r in result.reviewers:
        assert isinstance(r, ReviewerRecord)
        assert r.commitment_verified is True


@pytest.mark.asyncio
async def test_run_review_pipeline_mixed_consensus():
    r1 = _mock_verdict("APPROVE", "gpt-4o")
    r2 = _mock_verdict("REJECT", "gpt-4o")
    r3 = _mock_verdict("APPROVE", "claude")
    with patch.object(coordinator, "gpt4o_review", AsyncMock(side_effect=[r1, r2])), \
         patch.object(coordinator, "_call_claude_reviewer", AsyncMock(return_value=r3)):
        result = await run_review_pipeline(
            task_id=uuid.uuid4(), task_type="risk_analysis",
            payload={}, executor_output={},
        )
    assert result.consensus == "2_OF_3_APPROVE"
    assert result.all_verified is True


@pytest.mark.asyncio
async def test_run_review_pipeline_commitment_violation():
    """Force a SecurityViolationError via patched verify_commitment."""
    from core.review.hash_commitment import SecurityViolationError
    r1 = _mock_verdict("APPROVE")
    r2 = _mock_verdict("APPROVE")
    r3 = _mock_verdict("APPROVE")

    def _bad_verify(*args, **kwargs):
        raise SecurityViolationError("tampered")

    with patch.object(coordinator, "gpt4o_review", AsyncMock(side_effect=[r1, r2])), \
         patch.object(coordinator, "_call_claude_reviewer", AsyncMock(return_value=r3)), \
         patch.object(coordinator, "verify_commitment", _bad_verify):
        with pytest.raises(SecurityViolationError):
            await run_review_pipeline(
                task_id=uuid.uuid4(), task_type="document_review",
                payload={}, executor_output={},
            )
