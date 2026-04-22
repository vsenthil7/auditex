"""Tests for core.execution.context_manager."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest

from core.execution.context_manager import (
    ContextManager, ContextNotFoundError,
    DEFAULT_TTL_SECONDS, KEY_PREFIX, HISTORY_SUFFIX,
    _ctx_key, _history_key,
)


@pytest.fixture
def fake_redis():
    r = AsyncMock()
    r.set_json = AsyncMock()
    r.get_json = AsyncMock()
    r.delete = AsyncMock()
    r.exists = AsyncMock()
    return r


def test_key_helpers():
    tid = uuid.uuid4()
    assert _ctx_key(tid) == f"{KEY_PREFIX}{tid}"
    assert _history_key(tid).endswith(HISTORY_SUFFIX)


def test_default_ttl_positive():
    assert DEFAULT_TTL_SECONDS > 0


@pytest.mark.asyncio
async def test_create_with_initial_dict(fake_redis):
    cm = ContextManager(fake_redis, ttl_seconds=60)
    tid = uuid.uuid4()
    r = await cm.create(tid, initial={"a": 1})
    assert r["a"] == 1
    assert "__created_at__" in r
    assert fake_redis.set_json.await_count == 2
    # TTL forwarded
    first_call = fake_redis.set_json.await_args_list[0]
    assert first_call.kwargs["ttl_seconds"] == 60


@pytest.mark.asyncio
async def test_create_without_initial(fake_redis):
    cm = ContextManager(fake_redis)
    r = await cm.create(uuid.uuid4())
    assert "__created_at__" in r


@pytest.mark.asyncio
async def test_get_happy_path(fake_redis):
    fake_redis.get_json = AsyncMock(return_value={"x": 2})
    cm = ContextManager(fake_redis)
    r = await cm.get(uuid.uuid4())
    assert r == {"x": 2}


@pytest.mark.asyncio
async def test_get_raises_when_missing(fake_redis):
    fake_redis.get_json = AsyncMock(return_value=None)
    cm = ContextManager(fake_redis)
    with pytest.raises(ContextNotFoundError):
        await cm.get(uuid.uuid4())


@pytest.mark.asyncio
async def test_update_merges_into_existing(fake_redis):
    fake_redis.get_json = AsyncMock(return_value={"a": 1, "b": 2})
    cm = ContextManager(fake_redis)
    r = await cm.update(uuid.uuid4(), {"b": 99, "c": 3})
    assert r == {"a": 1, "b": 99, "c": 3}
    fake_redis.set_json.assert_awaited()


@pytest.mark.asyncio
async def test_update_raises_if_missing(fake_redis):
    fake_redis.get_json = AsyncMock(return_value=None)
    cm = ContextManager(fake_redis)
    with pytest.raises(ContextNotFoundError):
        await cm.update(uuid.uuid4(), {"x": 1})


@pytest.mark.asyncio
async def test_append_history_first_entry(fake_redis):
    fake_redis.get_json = AsyncMock(return_value=None)
    cm = ContextManager(fake_redis)
    r = await cm.append_history(uuid.uuid4(), "EXECUTE", note="ok")
    assert len(r) == 1
    assert r[0]["step"] == "EXECUTE"
    assert r[0]["note"] == "ok"
    assert "timestamp" in r[0]


@pytest.mark.asyncio
async def test_append_history_appends_to_existing(fake_redis):
    fake_redis.get_json = AsyncMock(return_value=[{"step": "OLD", "timestamp": "t", "note": None}])
    cm = ContextManager(fake_redis)
    r = await cm.append_history(uuid.uuid4(), "NEW")
    assert len(r) == 2
    assert r[0]["step"] == "OLD"
    assert r[1]["step"] == "NEW"
    assert r[1]["note"] is None


@pytest.mark.asyncio
async def test_get_history_missing_returns_empty(fake_redis):
    fake_redis.get_json = AsyncMock(return_value=None)
    cm = ContextManager(fake_redis)
    r = await cm.get_history(uuid.uuid4())
    assert r == []


@pytest.mark.asyncio
async def test_get_history_returns_list(fake_redis):
    fake_redis.get_json = AsyncMock(return_value=[{"step": "X"}])
    cm = ContextManager(fake_redis)
    r = await cm.get_history(uuid.uuid4())
    assert r == [{"step": "X"}]


@pytest.mark.asyncio
async def test_delete_removes_both_keys(fake_redis):
    cm = ContextManager(fake_redis)
    await cm.delete(uuid.uuid4())
    assert fake_redis.delete.await_count == 2


@pytest.mark.asyncio
async def test_exists_true(fake_redis):
    fake_redis.exists = AsyncMock(return_value=True)
    cm = ContextManager(fake_redis)
    assert await cm.exists(uuid.uuid4()) is True


@pytest.mark.asyncio
async def test_exists_false(fake_redis):
    fake_redis.exists = AsyncMock(return_value=False)
    cm = ContextManager(fake_redis)
    assert await cm.exists(uuid.uuid4()) is False
