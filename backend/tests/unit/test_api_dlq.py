"""Tests for app.api.v1.dlq route handlers."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.v1 import dlq as dlq_api


@pytest.fixture
def fake_entry():
    e = MagicMock()
    e.id = uuid.uuid4()
    e.task_id = uuid.uuid4()
    e.source_queue = "q"
    e.error_class = "E"
    e.error_message = "m"
    e.payload = {}
    e.attempt_count = 1
    e.status = "PENDING"
    e.created_at = datetime(2026, 4, 22, tzinfo=timezone.utc)
    e.resolved_at = None
    e.resolution_note = None
    return e


def test_entry_to_dict_full():
    e = MagicMock()
    e.id = uuid.uuid4()
    e.task_id = uuid.uuid4()
    e.source_queue = "q"
    e.error_class = "E"
    e.error_message = "m"
    e.payload = {"a": 1}
    e.attempt_count = 2
    e.status = "RETRYING"
    e.created_at = datetime(2026, 4, 22, tzinfo=timezone.utc)
    e.resolved_at = datetime(2026, 4, 23, tzinfo=timezone.utc)
    e.resolution_note = "ok"
    d = dlq_api._entry_to_dict(e)
    assert d["task_id"] == str(e.task_id)
    assert d["status"] == "RETRYING"
    assert d["created_at"] == "2026-04-22T00:00:00+00:00"
    assert d["resolved_at"] == "2026-04-23T00:00:00+00:00"
    assert d["resolution_note"] == "ok"


def test_entry_to_dict_with_no_task_id_no_timestamps():
    e = MagicMock()
    e.id = uuid.uuid4()
    e.task_id = None
    e.source_queue = "q"
    e.error_class = "E"
    e.error_message = "m"
    e.payload = {}
    e.attempt_count = 0
    e.status = "PENDING"
    e.created_at = None
    e.resolved_at = None
    e.resolution_note = None
    d = dlq_api._entry_to_dict(e)
    assert d["task_id"] is None
    assert d["created_at"] is None
    assert d["resolved_at"] is None


@pytest.mark.asyncio
async def test_list_dlq_entries_no_filter(mock_async_session, fake_entry):
    with patch.object(dlq_api.dlq_repo, "list_entries", AsyncMock(return_value=[fake_entry])):
        result = await dlq_api.list_dlq_entries(None, 100, {}, mock_async_session)
    assert result["count"] == 1
    assert len(result["entries"]) == 1


@pytest.mark.asyncio
async def test_list_dlq_entries_with_status(mock_async_session, fake_entry):
    spy = AsyncMock(return_value=[fake_entry])
    with patch.object(dlq_api.dlq_repo, "list_entries", spy):
        await dlq_api.list_dlq_entries("PENDING", 50, {}, mock_async_session)
    assert spy.await_args.kwargs["status"] == "PENDING"
    assert spy.await_args.kwargs["limit"] == 50


@pytest.mark.asyncio
async def test_get_dlq_entry_happy_path(mock_async_session, fake_entry):
    with patch.object(dlq_api.dlq_repo, "get_entry", AsyncMock(return_value=fake_entry)):
        r = await dlq_api.get_dlq_entry(fake_entry.id, {}, mock_async_session)
    assert r["id"] == str(fake_entry.id)


@pytest.mark.asyncio
async def test_get_dlq_entry_not_found(mock_async_session):
    with patch.object(dlq_api.dlq_repo, "get_entry", AsyncMock(return_value=None)):
        with pytest.raises(HTTPException) as e:
            await dlq_api.get_dlq_entry(uuid.uuid4(), {}, mock_async_session)
    assert e.value.status_code == 404


@pytest.mark.asyncio
async def test_retry_dlq_entry_happy_path(mock_async_session, fake_entry):
    fake_entry.status = "RETRYING"
    with patch.object(dlq_api.dlq_repo, "mark_retrying", AsyncMock(return_value=fake_entry)):
        r = await dlq_api.retry_dlq_entry(fake_entry.id, {}, mock_async_session)
    assert r["status"] == "RETRYING"
    mock_async_session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_retry_dlq_entry_not_found(mock_async_session):
    with patch.object(dlq_api.dlq_repo, "mark_retrying", AsyncMock(return_value=None)):
        with pytest.raises(HTTPException) as e:
            await dlq_api.retry_dlq_entry(uuid.uuid4(), {}, mock_async_session)
    assert e.value.status_code == 404


@pytest.mark.asyncio
async def test_resolve_dlq_entry_happy_path(mock_async_session, fake_entry):
    fake_entry.status = "RESOLVED"
    fake_entry.resolution_note = "fixed"
    with patch.object(dlq_api.dlq_repo, "mark_resolved", AsyncMock(return_value=fake_entry)):
        r = await dlq_api.resolve_dlq_entry(fake_entry.id, "fixed", {}, mock_async_session)
    assert r["status"] == "RESOLVED"
    mock_async_session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_resolve_dlq_entry_not_found(mock_async_session):
    with patch.object(dlq_api.dlq_repo, "mark_resolved", AsyncMock(return_value=None)):
        with pytest.raises(HTTPException) as e:
            await dlq_api.resolve_dlq_entry(uuid.uuid4(), None, {}, mock_async_session)
    assert e.value.status_code == 404
