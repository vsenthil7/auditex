"""Tests for db.connection: engine + session factory + dependency."""
from __future__ import annotations

import inspect
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from db import connection


def test_engine_exists():
    assert connection.engine is not None


def test_async_session_local_exists():
    assert connection.AsyncSessionLocal is not None


def test_get_db_session_is_async_generator():
    assert inspect.isasyncgenfunction(connection.get_db_session)


@pytest.mark.asyncio
async def test_get_db_session_happy_path():
    fake_session = AsyncMock()
    fake_session.commit = AsyncMock()
    fake_session.rollback = AsyncMock()
    fake_session.close = AsyncMock()

    fake_ctx = AsyncMock()
    fake_ctx.__aenter__ = AsyncMock(return_value=fake_session)
    fake_ctx.__aexit__ = AsyncMock(return_value=None)

    with patch.object(connection, "AsyncSessionLocal", MagicMock(return_value=fake_ctx)):
        agen = connection.get_db_session()
        s = await agen.__anext__()
        assert s is fake_session
        with pytest.raises(StopAsyncIteration):
            await agen.__anext__()

    fake_session.commit.assert_awaited()
    fake_session.close.assert_awaited()


@pytest.mark.asyncio
async def test_get_db_session_rolls_back_on_exception():
    fake_session = AsyncMock()
    fake_session.commit = AsyncMock()
    fake_session.rollback = AsyncMock()
    fake_session.close = AsyncMock()

    fake_ctx = AsyncMock()
    fake_ctx.__aenter__ = AsyncMock(return_value=fake_session)
    fake_ctx.__aexit__ = AsyncMock(return_value=None)

    with patch.object(connection, "AsyncSessionLocal", MagicMock(return_value=fake_ctx)):
        agen = connection.get_db_session()
        await agen.__anext__()
        with pytest.raises(RuntimeError):
            await agen.athrow(RuntimeError("boom"))

    fake_session.rollback.assert_awaited()
    fake_session.close.assert_awaited()
