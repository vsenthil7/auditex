"""Tests for app.api.middleware.rate_limit."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.middleware import rate_limit
from app.api.middleware.rate_limit import (
    RateLimitMiddleware,
    _identity,
    check_rate_limit,
    WINDOW_SECONDS,
    REDIS_KEY_PREFIX,
)


def _make_request(api_key: str | None = None, client_host: str | None = "1.2.3.4", path: str = "/api/v1/tasks"):
    req = MagicMock()
    req.headers = {"X-API-Key": api_key} if api_key else {}
    req.headers.get = lambda k, default=None: (api_key if (k == "X-API-Key" and api_key) else default)
    if client_host is None:
        req.client = None
    else:
        c = MagicMock()
        c.host = client_host
        req.client = c
    url = MagicMock()
    url.path = path
    req.url = url
    return req


# -------------------------------------------------------------
# _identity
# -------------------------------------------------------------
def test_identity_prefers_api_key():
    r = _make_request(api_key="mykey")
    assert _identity(r) == "k:mykey"


def test_identity_falls_back_to_client_host():
    r = _make_request(api_key=None, client_host="10.0.0.5")
    assert _identity(r) == "ip:10.0.0.5"


def test_identity_handles_missing_client():
    r = _make_request(api_key=None, client_host=None)
    assert _identity(r) == "ip:unknown"


# -------------------------------------------------------------
# check_rate_limit
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_check_rate_limit_zero_limit_always_allows():
    client = AsyncMock()
    allowed, remaining = await check_rate_limit(client, "k:x", 0)
    assert allowed is True
    assert remaining == -1
    client.zcard.assert_not_called()


@pytest.mark.asyncio
async def test_check_rate_limit_under_limit():
    client = AsyncMock()
    client.zremrangebyscore = AsyncMock(return_value=0)
    client.zcard = AsyncMock(return_value=3)
    client.zadd = AsyncMock(return_value=1)
    client.expire = AsyncMock(return_value=True)
    allowed, remaining = await check_rate_limit(client, "k:x", 10)
    assert allowed is True
    assert remaining == 6
    client.zadd.assert_awaited()
    client.expire.assert_awaited()


@pytest.mark.asyncio
async def test_check_rate_limit_at_limit_rejects():
    client = AsyncMock()
    client.zremrangebyscore = AsyncMock(return_value=0)
    client.zcard = AsyncMock(return_value=10)
    allowed, remaining = await check_rate_limit(client, "k:x", 10)
    assert allowed is False
    assert remaining == 0
    client.zadd.assert_not_called()


@pytest.mark.asyncio
async def test_check_rate_limit_over_limit_rejects():
    client = AsyncMock()
    client.zremrangebyscore = AsyncMock(return_value=0)
    client.zcard = AsyncMock(return_value=15)
    allowed, remaining = await check_rate_limit(client, "k:x", 10)
    assert allowed is False


# -------------------------------------------------------------
# RateLimitMiddleware.dispatch
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_dispatch_skips_health_path():
    mw = RateLimitMiddleware(app=None, redis_url="redis://fake", limit_per_min=5)
    req = _make_request(path="/api/v1/health")
    call_next = AsyncMock(return_value=MagicMock(headers={}))
    result = await mw.dispatch(req, call_next)
    call_next.assert_awaited_once_with(req)
    assert result is call_next.return_value


@pytest.mark.asyncio
async def test_dispatch_skips_docs_path():
    mw = RateLimitMiddleware(app=None, redis_url="redis://fake", limit_per_min=5)
    req = _make_request(path="/docs")
    call_next = AsyncMock(return_value=MagicMock(headers={}))
    await mw.dispatch(req, call_next)
    call_next.assert_awaited_once()


@pytest.mark.asyncio
async def test_dispatch_skips_openapi_path():
    mw = RateLimitMiddleware(app=None, redis_url="redis://fake", limit_per_min=5)
    req = _make_request(path="/openapi.json")
    call_next = AsyncMock(return_value=MagicMock(headers={}))
    await mw.dispatch(req, call_next)
    call_next.assert_awaited_once()


@pytest.mark.asyncio
async def test_dispatch_disabled_when_limit_zero():
    mw = RateLimitMiddleware(app=None, redis_url="redis://fake", limit_per_min=0)
    req = _make_request(api_key="k")
    call_next = AsyncMock(return_value=MagicMock(headers={}))
    await mw.dispatch(req, call_next)
    call_next.assert_awaited_once()


@pytest.mark.asyncio
async def test_dispatch_allows_under_limit_sets_headers():
    mw = RateLimitMiddleware(app=None, redis_url="redis://fake", limit_per_min=5)
    req = _make_request(api_key="k")
    resp = MagicMock()
    resp.headers = {}
    call_next = AsyncMock(return_value=resp)
    fake_client = AsyncMock()
    with patch.object(mw, "_get_client", AsyncMock(return_value=fake_client)), patch.object(rate_limit, "check_rate_limit", AsyncMock(return_value=(True, 4))):
        out = await mw.dispatch(req, call_next)
    assert out is resp
    assert out.headers["X-RateLimit-Limit"] == "5"
    assert out.headers["X-RateLimit-Remaining"] == "4"


@pytest.mark.asyncio
async def test_dispatch_at_limit_returns_429():
    mw = RateLimitMiddleware(app=None, redis_url="redis://fake", limit_per_min=5)
    req = _make_request(api_key="k")
    call_next = AsyncMock()
    fake_client = AsyncMock()
    p1 = patch.object(mw, "_get_client", AsyncMock(return_value=fake_client))
    p2 = patch.object(rate_limit, "check_rate_limit", AsyncMock(return_value=(False, 0)))
    with p1, p2:
        resp = await mw.dispatch(req, call_next)
    assert resp.status_code == 429
    assert resp.headers["Retry-After"] == str(WINDOW_SECONDS)
    assert resp.headers["X-RateLimit-Limit"] == "5"
    call_next.assert_not_awaited()


@pytest.mark.asyncio
async def test_dispatch_fails_open_on_redis_error():
    mw = RateLimitMiddleware(app=None, redis_url="redis://fake", limit_per_min=5)
    req = _make_request(api_key="k")
    resp = MagicMock(); resp.headers = {}
    call_next = AsyncMock(return_value=resp)
    p1 = patch.object(mw, "_get_client", AsyncMock(side_effect=RuntimeError("redis down")))
    with p1:
        out = await mw.dispatch(req, call_next)
    assert out is resp
    call_next.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_client_caches_connection():
    mw = RateLimitMiddleware(app=None, redis_url="redis://fake", limit_per_min=5)
    fake = MagicMock()
    with patch.object(rate_limit.aioredis, "from_url", return_value=fake) as mk:
        c1 = await mw._get_client()
        c2 = await mw._get_client()
    assert c1 is fake
    assert c2 is fake
    mk.assert_called_once()


def test_init_uses_settings_defaults_when_args_none():
    mw = RateLimitMiddleware(app=None)
    from app.config import settings
    assert mw._redis_url == settings.REDIS_URL
    assert mw._limit == settings.RATE_LIMIT_PER_MINUTE


def test_init_uses_explicit_args_when_provided():
    mw = RateLimitMiddleware(app=None, redis_url="redis://custom", limit_per_min=42)
    assert mw._redis_url == "redis://custom"
    assert mw._limit == 42


def test_constants_are_positive():
    assert WINDOW_SECONDS > 0
    assert REDIS_KEY_PREFIX.endswith(":")
