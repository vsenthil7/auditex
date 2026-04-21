"""Tests for core.reporting.poc_generator."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.reporting.poc_generator import (
    PoCReportData,
    _fallback_narrative,
    generate_report,
)


def test_fallback_narrative_has_expected_elements():
    out = _fallback_narrative(
        "document_review",
        {"model": "claude-sonnet-4-6", "confidence": 0.95},
        {"consensus": "3_OF_3_APPROVE", "reviewers": [{"model": "gpt-4o"}, {"model": "gpt-4o"}, {"model": "claude"}]},
    )
    assert "document_review" in out
    assert "claude-sonnet-4-6" in out
    assert "3_OF_3_APPROVE" in out
    assert "3" in out  # 3 reviewers


def test_fallback_narrative_missing_fields():
    out = _fallback_narrative("x", {}, {})
    assert "unknown" in out  # model default
    assert "x" in out


@pytest.mark.asyncio
async def test_generate_report_claude_success():
    fake_msg = MagicMock()
    fake_msg.content = [MagicMock(text="  Generated compliance narrative.  ")]

    with patch("core.reporting.poc_generator.call_claude", AsyncMock(return_value=fake_msg)):
        out = await generate_report(
            task_id=uuid.uuid4(),
            task_type="document_review",
            executor_output={"model": "claude", "confidence": 0.9},
            review_result={"consensus": "3_OF_3_APPROVE", "reviewers": []},
            vertex_event_hash="h" * 64,
            vertex_round=5,
            vertex_finalised_at="2026-04-21T18:00:00",
        )
    assert isinstance(out, PoCReportData)
    assert out.plain_english_summary == "Generated compliance narrative."


@pytest.mark.asyncio
async def test_generate_report_claude_fails_uses_fallback():
    with patch(
        "core.reporting.poc_generator.call_claude",
        AsyncMock(side_effect=RuntimeError("API down")),
    ):
        out = await generate_report(
            task_id=uuid.uuid4(),
            task_type="risk_analysis",
            executor_output={"model": "claude", "confidence": 0.5},
            review_result={"consensus": "2_OF_3_APPROVE", "reviewers": [{"model": "gpt-4o"}]},
            vertex_event_hash=None,
            vertex_round=None,
            vertex_finalised_at=None,
        )
    # Fallback narrative is used
    assert isinstance(out, PoCReportData)
    assert "risk_analysis" in out.plain_english_summary
    assert "2_OF_3_APPROVE" in out.plain_english_summary
