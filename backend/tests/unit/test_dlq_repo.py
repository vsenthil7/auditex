"""Tests for db.repositories.dlq_repo."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from db.models.dlq_entry import DLQEntry
from db.repositories import dlq_repo


@pytest.fixture
def fake_entry():
    e = MagicMock(spec=DLQEntry)
    e.id = uuid.uuid4()
    e.task_id = uuid.uuid4()
    e.source_queue = "execution_queue"
    e.error_class = "RuntimeError"
    e.error_message = "boom"
    e.payload = {"k": "v"}
    e.attempt_count = 3
    e.status = "PENDING"
    e.created_at = datetime(2026, 4, 22, tzinfo=timezone.utc)
    e.resolved_at = None
    e.resolution_note = None
    return e


@pytest.mark.asyncio
async def test_create_entry_basic(mock_async_session):
    task_id = uuid.uuid4()
    entry = await dlq_repo.create_entry(
        mock_async_session,
        task_id=task_id,
        source_queue="q",
        error_class="E",
        error_message="msg",
        payload={"a": 1},
        attempt_count=2,
    )
    assert entry.task_id == task_id
    assert entry.source_queue == "q"
    assert entry.error_class == "E"
    assert entry.payload == {"a": 1}
    assert entry.attempt_count == 2
    assert entry.status == "PENDING"
    mock_async_session.add.assert_called_once()
    mock_async_session.flush.assert_awaited()
    mock_async_session.refresh.assert_awaited()


@pytest.mark.asyncio
async def test_create_entry_payload_defaults_to_empty_dict(mock_async_session):
    entry = await dlq_repo.create_entry(
        mock_async_session, task_id=None, source_queue="q",
        error_class="E", error_message="m",
    )
    assert entry.payload == {}
    assert entry.task_id is None


@pytest.mark.asyncio
async def test_get_entry_found(mock_async_session, fake_entry):
    mock_async_session._result.scalar_one_or_none.return_value = fake_entry
    r = await dlq_repo.get_entry(mock_async_session, fake_entry.id)
    assert r is fake_entry


@pytest.mark.asyncio
async def test_get_entry_not_found(mock_async_session):
    mock_async_session._result.scalar_one_or_none.return_value = None
    r = await dlq_repo.get_entry(mock_async_session, uuid.uuid4())
    assert r is None


@pytest.mark.asyncio
async def test_list_entries_no_filter(mock_async_session, fake_entry):
    mock_async_session._result.scalars.return_value.all.return_value = [fake_entry]
    r = await dlq_repo.list_entries(mock_async_session, limit=50)
    assert list(r) == [fake_entry]


@pytest.mark.asyncio
async def test_list_entries_with_status(mock_async_session, fake_entry):
    mock_async_session._result.scalars.return_value.all.return_value = [fake_entry]
    r = await dlq_repo.list_entries(mock_async_session, status="PENDING", limit=10)
    assert list(r) == [fake_entry]


@pytest.mark.asyncio
async def test_mark_resolved_happy_path(mock_async_session, fake_entry):
    mock_async_session._result.scalar_one_or_none.return_value = fake_entry
    r = await dlq_repo.mark_resolved(mock_async_session, fake_entry.id, resolution_note="fixed")
    assert r is fake_entry
    assert fake_entry.status == "RESOLVED"
    assert fake_entry.resolution_note == "fixed"
    assert isinstance(fake_entry.resolved_at, datetime)


@pytest.mark.asyncio
async def test_mark_resolved_not_found(mock_async_session):
    mock_async_session._result.scalar_one_or_none.return_value = None
    r = await dlq_repo.mark_resolved(mock_async_session, uuid.uuid4())
    assert r is None


@pytest.mark.asyncio
async def test_mark_retrying_happy_path(mock_async_session, fake_entry):
    fake_entry.attempt_count = 5
    mock_async_session._result.scalar_one_or_none.return_value = fake_entry
    r = await dlq_repo.mark_retrying(mock_async_session, fake_entry.id)
    assert r is fake_entry
    assert fake_entry.status == "RETRYING"
    assert fake_entry.attempt_count == 6


@pytest.mark.asyncio
async def test_mark_retrying_not_found(mock_async_session):
    mock_async_session._result.scalar_one_or_none.return_value = None
    r = await dlq_repo.mark_retrying(mock_async_session, uuid.uuid4())
    assert r is None
