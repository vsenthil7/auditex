"""Tests for core.reporting.eu_act_formatter."""
from __future__ import annotations

import json

from core.reporting.eu_act_formatter import (
    _RISK_HIGH_THRESHOLD,
    _RISK_MEDIUM_THRESHOLD,
    _confidence_to_risk,
    format_eu_ai_act,
)


def test_confidence_to_risk_unknown():
    assert _confidence_to_risk(None) == "UNKNOWN"


def test_confidence_to_risk_high():
    assert _confidence_to_risk(0.3) == "HIGH"


def test_confidence_to_risk_medium():
    assert _confidence_to_risk(0.7) == "MEDIUM"


def test_confidence_to_risk_low():
    assert _confidence_to_risk(0.95) == "LOW"


def test_format_eu_ai_act_happy_path():
    out = format_eu_ai_act(
        task_type="document_review",
        executor_output={
            "model": "claude-sonnet-4-6",
            "confidence": 0.9,
            "output": {
                "recommendation": "APPROVE",
                "reasoning": "All fields present.",
            },
        },
        review_result={
            "consensus": "3_OF_3_APPROVE",
            "reviewers": [
                {"model": "gpt-4o", "verdict": "APPROVE", "confidence": 0.9, "commitment_verified": True},
                {"model": "gpt-4o", "verdict": "APPROVE", "confidence": 0.88, "commitment_verified": True},
                {"model": "claude", "verdict": "APPROVE", "confidence": 0.85, "commitment_verified": True},
            ],
        },
        vertex_event_hash="h" * 64,
        vertex_round=5,
        vertex_finalised_at="2026-04-21T18:00:00",
    )
    assert out["article_9_risk_management"]["task_type"] == "document_review"
    assert out["article_9_risk_management"]["risk_assessment"] == "LOW"
    assert out["article_13_transparency"]["decision_made"] == "APPROVE"
    assert out["article_13_transparency"]["consensus"] == "3_OF_3_APPROVE"
    assert out["article_17_quality_management"]["all_commitments_verified"] is True
    assert out["article_17_quality_management"]["vertex_event_hash"] == "h" * 64


def test_format_eu_ai_act_confidence_string_bad():
    out = format_eu_ai_act(
        task_type="document_review",
        executor_output={"model": "x", "confidence": "not_a_number", "output": {}},
        review_result={"consensus": "x", "reviewers": []},
        vertex_event_hash=None, vertex_round=None, vertex_finalised_at=None,
    )
    assert out["article_9_risk_management"]["confidence_score"] is None
    assert out["article_9_risk_management"]["risk_assessment"] == "UNKNOWN"


def test_format_eu_ai_act_output_is_string():
    out = format_eu_ai_act(
        task_type="risk_analysis",
        executor_output={
            "model": "claude",
            "confidence": 0.5,
            "output": json.dumps({"recommendation": "REJECT", "reasoning": "r"}),
        },
        review_result={"consensus": "x", "reviewers": []},
        vertex_event_hash=None, vertex_round=None, vertex_finalised_at=None,
    )
    assert out["article_13_transparency"]["decision_made"] == "REJECT"


def test_format_eu_ai_act_output_is_unparseable_string():
    out = format_eu_ai_act(
        task_type="risk_analysis",
        executor_output={"model": "claude", "confidence": 0.5, "output": "not json"},
        review_result={"consensus": "x", "reviewers": []},
        vertex_event_hash=None, vertex_round=None, vertex_finalised_at=None,
    )
    assert out["article_13_transparency"]["decision_made"] == ""


def test_format_eu_ai_act_falls_back_to_summary():
    out = format_eu_ai_act(
        task_type="risk_analysis",
        executor_output={
            "model": "claude",
            "confidence": 0.8,
            "output": {
                "recommendation": "APPROVE",
                "summary": "alt summary text",  # no `reasoning` key
            },
        },
        review_result={"consensus": "x", "reviewers": []},
        vertex_event_hash=None, vertex_round=None, vertex_finalised_at=None,
    )
    assert "alt summary text" in out["article_13_transparency"]["reasoning_summary"]


def test_format_eu_ai_act_falls_back_to_joined_strings():
    out = format_eu_ai_act(
        task_type="risk_analysis",
        executor_output={
            "model": "claude",
            "confidence": 0.8,
            "output": {"field_a": "valueA", "field_b": "valueB"},  # no reasoning / summary
        },
        review_result={"consensus": "x", "reviewers": []},
        vertex_event_hash=None, vertex_round=None, vertex_finalised_at=None,
    )
    joined = out["article_13_transparency"]["reasoning_summary"]
    assert "valueA" in joined
    assert "valueB" in joined


def test_format_eu_ai_act_reviewers_with_missing_fields():
    out = format_eu_ai_act(
        task_type="risk_analysis",
        executor_output={"model": "claude", "confidence": 0.8, "output": {}},
        review_result={
            "consensus": "3_OF_3_APPROVE",
            "reviewers": [
                {},  # totally empty reviewer entry exercises defaults
            ],
        },
        vertex_event_hash=None, vertex_round=None, vertex_finalised_at=None,
    )
    assert out["article_13_transparency"]["reviewers"][0]["model"] == "unknown"
    assert out["article_13_transparency"]["reviewers"][0]["verdict"] == "UNKNOWN"


def test_thresholds_are_sane():
    assert 0 < _RISK_HIGH_THRESHOLD < _RISK_MEDIUM_THRESHOLD <= 1.0
