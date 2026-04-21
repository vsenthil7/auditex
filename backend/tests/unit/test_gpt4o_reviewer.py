"""Tests for core.review.gpt4o_reviewer."""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.review.gpt4o_reviewer import ReviewVerdict, review_output


def _make_completion(content_str: str, model="gpt-4o"):
    c = MagicMock()
    c.choices = [MagicMock(message=MagicMock(content=content_str))]
    c.model = model
    return c


@pytest.mark.asyncio
async def test_review_output_success_approve():
    comp = _make_completion(json.dumps({
        "verdict": "APPROVE", "reasoning": "All good.", "confidence": 0.9,
    }))
    with patch("core.review.gpt4o_reviewer.call_openai", AsyncMock(return_value=comp)):
        v = await review_output(
            task_type="document_review", original_payload={"x": 1}, executor_output={"y": 2},
        )
    assert isinstance(v, ReviewVerdict)
    assert v.verdict == "APPROVE"
    assert v.confidence == 0.9


@pytest.mark.asyncio
async def test_review_output_reject_lowercase_normalised():
    comp = _make_completion(json.dumps({
        "verdict": "reject", "reasoning": "Bad.", "confidence": 0.6,
    }))
    with patch("core.review.gpt4o_reviewer.call_openai", AsyncMock(return_value=comp)):
        v = await review_output(
            task_type="risk_analysis", original_payload={}, executor_output={},
        )
    assert v.verdict == "REJECT"


@pytest.mark.asyncio
async def test_review_output_invalid_json_raises():
    comp = _make_completion("not json at all")
    with patch("core.review.gpt4o_reviewer.call_openai", AsyncMock(return_value=comp)):
        with pytest.raises(ValueError):
            await review_output(
                task_type="document_review", original_payload={}, executor_output={},
            )


@pytest.mark.asyncio
async def test_review_output_invalid_verdict_raises():
    comp = _make_completion(json.dumps({
        "verdict": "MAYBE", "reasoning": "idk", "confidence": 0.5,
    }))
    with patch("core.review.gpt4o_reviewer.call_openai", AsyncMock(return_value=comp)):
        with pytest.raises(ValueError):
            await review_output(
                task_type="document_review", original_payload={}, executor_output={},
            )


@pytest.mark.asyncio
async def test_review_output_confidence_out_of_range_raises():
    comp = _make_completion(json.dumps({
        "verdict": "APPROVE", "reasoning": "x", "confidence": 5.0,
    }))
    with patch("core.review.gpt4o_reviewer.call_openai", AsyncMock(return_value=comp)):
        with pytest.raises(ValueError):
            await review_output(
                task_type="document_review", original_payload={}, executor_output={},
            )


@pytest.mark.asyncio
async def test_review_output_empty_choices():
    comp = MagicMock()
    comp.choices = []
    comp.model = "gpt-4o"
    with patch("core.review.gpt4o_reviewer.call_openai", AsyncMock(return_value=comp)):
        with pytest.raises(ValueError):
            await review_output(
                task_type="document_review", original_payload={}, executor_output={},
            )


@pytest.mark.asyncio
async def test_review_output_empty_reasoning_raises():
    comp = _make_completion(json.dumps({
        "verdict": "APPROVE", "reasoning": "", "confidence": 0.5,
    }))
    with patch("core.review.gpt4o_reviewer.call_openai", AsyncMock(return_value=comp)):
        with pytest.raises(ValueError):
            await review_output(
                task_type="document_review", original_payload={}, executor_output={},
            )
