"""Tests for app.api.middleware.auth."""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.middleware import auth
from app.api.middleware.auth import _get_redis, require_api_key


@pytest.fixture(autouse=True)
def _reset_redis_singleton():
    # Reset module-level client between tests
    auth._redis_client = None
    yield
    auth._redis_client = None


def test_get_redis_creates_client_once():
    fake_client = MagicMock()
    with patch("redis.asyncio.from_url", return_value=fake_client) as m:
        c1 = _get_redis()
        c2 = _get_redis()
    assert c1 is fake_client
    assert c1 is c2
    m.assert_called_once()


@pytest.mark.asyncio
async def test_require_api_key_missing_raises_401():
    with pytest.raises(HTTPException) as exc_info:
        await require_api_key(api_key=None)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_require_api_key_valid():
    fake_redis = MagicMock()
    fake_redis.get = AsyncMock(return_value=json.dumps({
        "key_id": "test-phase2",
        "created_at": "2026-01-01T00:00:00",
    }))
    with patch.object(auth, "_get_redis", return_value=fake_redis):
        meta = await require_api_key(api_key="good-key")
    assert meta["key_id"] == "test-phase2"


@pytest.mark.asyncio
async def test_require_api_key_invalid_raises_401():
    fake_redis = MagicMock()
    fake_redis.get = AsyncMock(return_value=None)
    with patch.object(auth, "_get_redis", return_value=fake_redis):
        with pytest.raises(HTTPException) as exc_info:
            await require_api_key(api_key="bad-key")
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_require_api_key_redis_error_raises_503():
    fake_redis = MagicMock()
    fake_redis.get = AsyncMock(side_effect=RuntimeError("Redis down"))
    with patch.object(auth, "_get_redis", return_value=fake_redis):
        with pytest.raises(HTTPException) as exc_info:
            await require_api_key(api_key="k")
    assert exc_info.value.status_code == 503


@pytest.mark.asyncio
async def test_require_api_key_corrupt_json_raises_500():
    fake_redis = MagicMock()
    fake_redis.get = AsyncMock(return_value="not valid json {{{")
    with patch.object(auth, "_get_redis", return_value=fake_redis):
        with pytest.raises(HTTPException) as exc_info:
            await require_api_key(api_key="k")
    assert exc_info.value.status_code == 500
