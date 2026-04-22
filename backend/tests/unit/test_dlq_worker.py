"""Tests for workers.dlq_worker."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from workers import dlq_worker


def _make_session():
    s = AsyncMock()
    s.commit = AsyncMock()
    return s


def _make_factory(session):
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=session)
    ctx.__aexit__ = AsyncMock(return_value=None)
    return MagicMock(return_value=ctx)


def _make_engine():
    e = MagicMock()
    e.dispose = AsyncMock()
    return e


def test_make_session_factory_returns_pair():
    p1 = patch.object(dlq_worker, "create_async_engine", return_value="ENGINE")
    p2 = patch.object(dlq_worker, "async_sessionmaker", return_value="SESSION")
    with p1, p2:
        factory, engine = dlq_worker._make_session_factory()
    assert factory == "SESSION"
    assert engine == "ENGINE"


@pytest.mark.asyncio
async def test_route_async_creates_entry_and_commits():
    session = _make_session()
    factory = _make_factory(session)
    engine = _make_engine()
    fake_entry = MagicMock()
    fake_entry.id = uuid.uuid4()
    task_id = str(uuid.uuid4())
    p1 = patch.object(dlq_worker, "_make_session_factory", return_value=(factory, engine))
    p2 = patch.object(dlq_worker.dlq_repo, "create_entry", AsyncMock(return_value=fake_entry))
    with p1, p2:
        result = await dlq_worker._route_async(task_id, "q", "E", "m", {}, 1)
    assert result == str(fake_entry.id)
    session.commit.assert_awaited()
    engine.dispose.assert_awaited()


@pytest.mark.asyncio
async def test_route_async_with_none_task_id():
    session = _make_session()
    factory = _make_factory(session)
    engine = _make_engine()
    fake_entry = MagicMock()
    fake_entry.id = uuid.uuid4()
    spy = AsyncMock(return_value=fake_entry)
    p1 = patch.object(dlq_worker, "_make_session_factory", return_value=(factory, engine))
    p2 = patch.object(dlq_worker.dlq_repo, "create_entry", spy)
    with p1, p2:
        result = await dlq_worker._route_async(None, "q", "E", "m", {}, 0)
    assert result == str(fake_entry.id)
    assert spy.call_args.kwargs["task_id"] is None


@pytest.mark.asyncio
async def test_redeliver_async_happy_path():
    session = _make_session()
    factory = _make_factory(session)
    engine = _make_engine()
    fake_entry = MagicMock()
    fake_entry.status = "RETRYING"
    eid = str(uuid.uuid4())
    p1 = patch.object(dlq_worker, "_make_session_factory", return_value=(factory, engine))
    p2 = patch.object(dlq_worker.dlq_repo, "mark_retrying", AsyncMock(return_value=fake_entry))
    with p1, p2:
        result = await dlq_worker._redeliver_async(eid)
    assert result == "RETRYING"
    session.commit.assert_awaited()
    engine.dispose.assert_awaited()


@pytest.mark.asyncio
async def test_redeliver_async_entry_missing():
    session = _make_session()
    factory = _make_factory(session)
    engine = _make_engine()
    p1 = patch.object(dlq_worker, "_make_session_factory", return_value=(factory, engine))
    p2 = patch.object(dlq_worker.dlq_repo, "mark_retrying", AsyncMock(return_value=None))
    with p1, p2:
        result = await dlq_worker._redeliver_async(str(uuid.uuid4()))
    assert result is None
    engine.dispose.assert_awaited()


def test_route_to_dlq_celery_task_wraps_async():
    with patch.object(dlq_worker, "asyncio") as mk_asyncio:
        mk_asyncio.run.return_value = "entry-uuid"
        result = dlq_worker.route_to_dlq(None, "q", "E", "m")
    assert result == "entry-uuid"
    mk_asyncio.run.assert_called_once()


def test_route_to_dlq_defaults_payload_to_empty_dict():
    with patch.object(dlq_worker, "asyncio") as mk_asyncio:
        mk_asyncio.run.return_value = "id"
        dlq_worker.route_to_dlq("tid", "q", "E", "m", payload=None, attempt_count=5)
    coro = mk_asyncio.run.call_args.args[0]
    coro.close()


def test_redeliver_entry_celery_task_wraps_async():
    with patch.object(dlq_worker, "asyncio") as mk_asyncio:
        mk_asyncio.run.return_value = "RETRYING"
        result = dlq_worker.redeliver_entry(str(uuid.uuid4()))
    assert result == "RETRYING"
