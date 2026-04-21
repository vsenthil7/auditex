"""Tests for db.repositories.event_repo (INSERT-only audit log)."""
from __future__ import annotations

import json
import uuid

import pytest

from db.repositories import event_repo


@pytest.mark.asyncio
async def test_insert_event_minimal(mock_async_session):
    evt = await event_repo.insert_event(
        mock_async_session, event_type="task_submitted",
    )
    assert evt.event_type == "task_submitted"
    assert json.loads(evt.payload_json) == {}
    mock_async_session.add.assert_called_once()
    mock_async_session.flush.assert_awaited()


@pytest.mark.asyncio
async def test_insert_event_full_payload(mock_async_session):
    tid = uuid.uuid4()
    aid = uuid.uuid4()
    evt = await event_repo.insert_event(
        mock_async_session,
        event_type="task_completed",
        task_id=tid,
        actor_agent_id=aid,
        actor_type="claude",
        payload={"model": "claude", "confidence": 0.95},
        sequence=5,
    )
    assert evt.task_id == tid
    assert evt.actor_agent_id == aid
    assert evt.actor_type == "claude"
    assert evt.sequence == 5
    assert json.loads(evt.payload_json)["confidence"] == 0.95


@pytest.mark.asyncio
async def test_get_events_for_task_empty(mock_async_session):
    mock_async_session._scalars.all.return_value = []
    evts = await event_repo.get_events_for_task(mock_async_session, uuid.uuid4())
    assert evts == []


@pytest.mark.asyncio
async def test_get_events_for_task_with_results(mock_async_session):
    from unittest.mock import MagicMock
    e1 = MagicMock()
    e2 = MagicMock()
    mock_async_session._scalars.all.return_value = [e1, e2]
    evts = await event_repo.get_events_for_task(mock_async_session, uuid.uuid4())
    assert len(evts) == 2


def test_event_repo_has_no_delete_method():
    assert not hasattr(event_repo, "delete_event")


def test_event_repo_has_no_update_method():
    assert not hasattr(event_repo, "update_event")
