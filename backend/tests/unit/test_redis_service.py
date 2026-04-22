"""Tests for services.redis_service."""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services import redis_service
from services.redis_service import (
    RedisService, RedisServiceError,
    get_redis_service, reset_default_service,
)


@pytest.fixture(autouse=True)
def _reset_singleton():
    reset_default_service()
    yield
    reset_default_service()


@pytest.mark.asyncio
async def test_get_client_lazy_and_cached():
    svc = RedisService(url="redis://x")
    fake = MagicMock()
    with patch.object(redis_service.aioredis, "from_url", return_value=fake) as mk:
        c1 = await svc._get_client()
        c2 = await svc._get_client()
    assert c1 is fake and c2 is fake
    mk.assert_called_once()


@pytest.mark.asyncio
async def test_close_clears_client_and_calls_aclose():
    svc = RedisService(url="redis://x")
    fake = MagicMock(); fake.aclose = AsyncMock()
    svc._client = fake
    await svc.close()
    fake.aclose.assert_awaited()
    assert svc._client is None


@pytest.mark.asyncio
async def test_close_is_noop_when_no_client():
    svc = RedisService(url="redis://x")
    # Should not raise even though _client is None
    await svc.close()
    assert svc._client is None


@pytest.mark.asyncio
async def test_set_json_no_ttl():
    svc = RedisService(url="redis://x")
    fake = AsyncMock(); svc._client = fake
    await svc.set_json("k", {"a": 1})
    fake.set.assert_awaited()
    args, kwargs = fake.set.await_args
    assert args[0] == "k"
    assert json.loads(args[1]) == {"a": 1}
    assert "ex" not in kwargs


@pytest.mark.asyncio
async def test_set_json_with_ttl():
    svc = RedisService(url="redis://x")
    fake = AsyncMock(); svc._client = fake
    await svc.set_json("k", {"a": 1}, ttl_seconds=30)
    kwargs = fake.set.await_args.kwargs
    assert kwargs["ex"] == 30


@pytest.mark.asyncio
async def test_set_json_wraps_exceptions():
    svc = RedisService(url="redis://x")
    fake = AsyncMock(); fake.set = AsyncMock(side_effect=RuntimeError("down"))
    svc._client = fake
    with pytest.raises(RedisServiceError):
        await svc.set_json("k", {})


@pytest.mark.asyncio
async def test_get_json_returns_parsed_value():
    svc = RedisService(url="redis://x")
    fake = AsyncMock(); fake.get = AsyncMock(return_value='{"a": 1}')
    svc._client = fake
    r = await svc.get_json("k")
    assert r == {"a": 1}


@pytest.mark.asyncio
async def test_get_json_missing_key_returns_none():
    svc = RedisService(url="redis://x")
    fake = AsyncMock(); fake.get = AsyncMock(return_value=None)
    svc._client = fake
    r = await svc.get_json("k")
    assert r is None


@pytest.mark.asyncio
async def test_get_json_bad_json_raises():
    svc = RedisService(url="redis://x")
    fake = AsyncMock(); fake.get = AsyncMock(return_value="not json")
    svc._client = fake
    with pytest.raises(RedisServiceError):
        await svc.get_json("k")


@pytest.mark.asyncio
async def test_get_json_transport_error_wrapped():
    svc = RedisService(url="redis://x")
    fake = AsyncMock(); fake.get = AsyncMock(side_effect=ConnectionError("no"))
    svc._client = fake
    with pytest.raises(RedisServiceError):
        await svc.get_json("k")


@pytest.mark.asyncio
async def test_delete_happy_path():
    svc = RedisService(); fake = AsyncMock(); fake.delete = AsyncMock(return_value=1); svc._client = fake
    r = await svc.delete("k")
    assert r == 1


@pytest.mark.asyncio
async def test_delete_wraps_exceptions():
    svc = RedisService(); fake = AsyncMock(); fake.delete = AsyncMock(side_effect=RuntimeError("x")); svc._client = fake
    with pytest.raises(RedisServiceError):
        await svc.delete("k")


@pytest.mark.asyncio
async def test_exists_true():
    svc = RedisService(); fake = AsyncMock(); fake.exists = AsyncMock(return_value=1); svc._client = fake
    assert await svc.exists("k") is True


@pytest.mark.asyncio
async def test_exists_false():
    svc = RedisService(); fake = AsyncMock(); fake.exists = AsyncMock(return_value=0); svc._client = fake
    assert await svc.exists("k") is False


@pytest.mark.asyncio
async def test_exists_wraps_exceptions():
    svc = RedisService(); fake = AsyncMock(); fake.exists = AsyncMock(side_effect=RuntimeError("x")); svc._client = fake
    with pytest.raises(RedisServiceError):
        await svc.exists("k")


@pytest.mark.asyncio
async def test_incr_returns_new_value():
    svc = RedisService(); fake = AsyncMock(); fake.incrby = AsyncMock(return_value=7); svc._client = fake
    r = await svc.incr("k", amount=3)
    assert r == 7
    fake.incrby.assert_awaited_with("k", 3)


@pytest.mark.asyncio
async def test_incr_wraps_exceptions():
    svc = RedisService(); fake = AsyncMock(); fake.incrby = AsyncMock(side_effect=RuntimeError("x")); svc._client = fake
    with pytest.raises(RedisServiceError):
        await svc.incr("k")


@pytest.mark.asyncio
async def test_expire_true_and_false():
    svc = RedisService(); fake = AsyncMock(); fake.expire = AsyncMock(return_value=1); svc._client = fake
    assert await svc.expire("k", 10) is True
    fake.expire = AsyncMock(return_value=0); svc._client = fake
    assert await svc.expire("k", 10) is False


@pytest.mark.asyncio
async def test_expire_wraps_exceptions():
    svc = RedisService(); fake = AsyncMock(); fake.expire = AsyncMock(side_effect=RuntimeError("x")); svc._client = fake
    with pytest.raises(RedisServiceError):
        await svc.expire("k", 10)


def test_get_redis_service_returns_singleton():
    s1 = get_redis_service()
    s2 = get_redis_service()
    assert s1 is s2
    assert isinstance(s1, RedisService)


def test_reset_default_service_clears_singleton():
    s1 = get_redis_service()
    reset_default_service()
    s2 = get_redis_service()
    assert s1 is not s2


def test_default_url_from_settings():
    from app.config import settings
    svc = RedisService()
    assert svc._url == settings.REDIS_URL


def test_custom_url_respected():
    svc = RedisService(url="redis://custom:6379")
    assert svc._url == "redis://custom:6379"
