"""Tests for core.consensus.event_builder."""
from __future__ import annotations

import uuid
from types import SimpleNamespace

from core.consensus.event_builder import build_task_completed_event, _sha256_of_json


def _make_review_result(executor_confidence=0.9):
    reviewer_1 = SimpleNamespace(model="gpt-4o", verdict="APPROVE", committed_hash="h1")
    reviewer_2 = SimpleNamespace(model="gpt-4o", verdict="APPROVE", committed_hash="h2")
    reviewer_3 = SimpleNamespace(model="claude", verdict="REJECT", committed_hash="h3")
    return SimpleNamespace(
        reviewers=[reviewer_1, reviewer_2, reviewer_3],
        consensus="2_OF_3_APPROVE",
        all_verified=True,
        executor_confidence=executor_confidence,
    )


def test_sha256_of_json_deterministic():
    a = _sha256_of_json({"a": 1, "b": 2})
    b = _sha256_of_json({"b": 2, "a": 1})
    assert a == b


def test_build_task_completed_event_full():
    tid = str(uuid.uuid4())
    payload = build_task_completed_event(
        task_id=tid,
        task_type="document_review",
        executor_output={"recommendation": "APPROVE"},
        review_result=_make_review_result(0.9),
    )
    assert payload["event_type"] == "task_completed"
    assert payload["task_id"] == tid
    assert payload["schema_version"] == "1.0"
    assert payload["executor"]["model"] == "claude-sonnet-4-6"
    assert payload["executor"]["confidence"] == 0.9
    assert len(payload["reviewers"]) == 3
    assert payload["consensus"] == "2_OF_3_APPROVE"
    assert payload["all_commitments_verified"] is True


def test_build_task_completed_event_confidence_invalid():
    rr = _make_review_result(executor_confidence="not a number")
    payload = build_task_completed_event(
        task_id="t1",
        task_type="risk_analysis",
        executor_output={"risk_level": "LOW"},
        review_result=rr,
    )
    assert payload["executor"]["confidence"] is None


def test_build_task_completed_event_missing_executor_confidence():
    rr = SimpleNamespace(
        reviewers=[],
        consensus="0_OF_3_APPROVE",
        all_verified=False,
    )  # no executor_confidence attribute
    payload = build_task_completed_event(
        task_id="t1", task_type="x", executor_output={}, review_result=rr,
    )
    assert payload["executor"]["confidence"] is None
    assert payload["reviewers"] == []


def test_build_task_completed_event_reviewers_missing():
    rr = SimpleNamespace(consensus="x", all_verified=False, executor_confidence=0.5)
    # no .reviewers → AttributeError caught → reviewers = []
    payload = build_task_completed_event(
        task_id="t", task_type="x", executor_output={}, review_result=rr,
    )
    assert payload["reviewers"] == []
