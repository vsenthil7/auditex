"""Tests for app.api.v1.events route handlers (Phase 12 Step 3a)."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.v1 import events as events_api
from core.consensus.proof_verifier import EmptyEventChain, VerificationResult


class _MockResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


def _make_session_returning(task_value):
    """Build a mock AsyncSession whose ``execute()`` returns ``task_value``."""
    sess = MagicMock()
    sess.execute = AsyncMock(return_value=_MockResult(task_value))
    return sess


@pytest.mark.asyncio
async def test_verify_task_not_found():
    sess = _make_session_returning(None)
    with pytest.raises(HTTPException) as exc:
        await events_api.verify_task_proof_endpoint(
            task_id=uuid.uuid4(), _key_meta={}, session=sess,
        )
    assert exc.value.status_code == 404
    assert "not found" in exc.value.detail.lower()


@pytest.mark.asyncio
async def test_verify_task_without_vertex_hash():
    task = MagicMock()
    task.vertex_event_hash = None
    sess = _make_session_returning(task)
    with pytest.raises(HTTPException) as exc:
        await events_api.verify_task_proof_endpoint(
            task_id=uuid.uuid4(), _key_meta={}, session=sess,
        )
    assert exc.value.status_code == 404
    assert "vertex event hash" in exc.value.detail.lower()


@pytest.mark.asyncio
async def test_verify_task_empty_chain():
    task = MagicMock()
    task.vertex_event_hash = "abc123"
    sess = _make_session_returning(task)

    with patch.object(
        events_api.event_repo,
        "get_events_for_task",
        AsyncMock(return_value=[]),
    ):
        # Force the proof_verifier to raise EmptyEventChain by having no events
        with patch.object(
            events_api,
            "verify_task_proof",
            side_effect=EmptyEventChain("empty"),
        ):
            result = await events_api.verify_task_proof_endpoint(
                task_id=uuid.uuid4(), _key_meta={}, session=sess,
            )
    assert result["verified"] is False
    assert result["event_count"] == 0
    assert result["reason"] == "event chain is empty -- nothing to hash"
    names = [c["name"] for c in result["checks"]]
    assert names == ["has_expected_hash", "has_events", "chain_hash_matches"]
    assert result["checks"][1]["ok"] is False


@pytest.mark.asyncio
async def test_verify_task_happy_path_matches():
    task = MagicMock()
    task.vertex_event_hash = "expected_hash_value"
    sess = _make_session_returning(task)
    fake_events = [MagicMock(), MagicMock(), MagicMock()]
    vr = VerificationResult(
        verified=True,
        expected_hash="expected_hash_value",
        computed_hash="expected_hash_value",
        event_count=3,
        reason=None,
    )
    with patch.object(
        events_api.event_repo,
        "get_events_for_task",
        AsyncMock(return_value=fake_events),
    ):
        with patch.object(events_api, "verify_task_proof", return_value=vr):
            result = await events_api.verify_task_proof_endpoint(
                task_id=uuid.uuid4(), _key_meta={}, session=sess,
            )
    assert result["verified"] is True
    assert result["computed_hash"] == "expected_hash_value"
    assert result["event_count"] == 3
    assert all(c["ok"] for c in result["checks"])


@pytest.mark.asyncio
async def test_verify_task_hash_mismatch():
    task = MagicMock()
    task.vertex_event_hash = "expected_hash"
    sess = _make_session_returning(task)
    fake_events = [MagicMock(), MagicMock()]
    vr = VerificationResult(
        verified=False,
        expected_hash="expected_hash",
        computed_hash="computed_differs",
        event_count=2,
        reason="chain hash does not match expected hash (tampered or wrong events)",
    )
    with patch.object(
        events_api.event_repo,
        "get_events_for_task",
        AsyncMock(return_value=fake_events),
    ):
        with patch.object(events_api, "verify_task_proof", return_value=vr):
            result = await events_api.verify_task_proof_endpoint(
                task_id=uuid.uuid4(), _key_meta={}, session=sess,
            )
    assert result["verified"] is False
    assert result["computed_hash"] == "computed_differs"
    # has_expected_hash + has_events should be OK, chain_hash_matches not
    assert result["checks"][0]["ok"] is True
    assert result["checks"][1]["ok"] is True
    assert result["checks"][2]["ok"] is False
    assert "tampered" in result["reason"]
