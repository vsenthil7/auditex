"""Tests for app.api.v1.health."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.v1 import health


@pytest.mark.asyncio
async def test_health_basic():
    out = await health.health_basic()
    assert out["status"] == "healthy"
    assert out["version"] == "0.1.0"


@pytest.mark.asyncio
async def test_health_deep_all_green():
    # Mock DB conn
    fake_conn = AsyncMock()
    fake_result = MagicMock()
    fake_result.fetchall.return_value = [
        ("agents",), ("tasks",), ("audit_events",), ("reports",), ("alembic_version",),
    ]
    fake_conn.execute = AsyncMock(return_value=fake_result)

    fake_engine_ctx = MagicMock()
    fake_engine_ctx.__aenter__ = AsyncMock(return_value=fake_conn)
    fake_engine_ctx.__aexit__ = AsyncMock(return_value=None)

    fake_engine = MagicMock()
    fake_engine.connect = MagicMock(return_value=fake_engine_ctx)

    fake_redis = MagicMock()
    fake_redis.ping = AsyncMock()
    fake_redis.aclose = AsyncMock()

    fake_reader = MagicMock()
    fake_writer = MagicMock()
    fake_writer.close = MagicMock()
    fake_writer.wait_closed = AsyncMock()

    async def fake_open_connection(host, port):
        return fake_reader, fake_writer

    with patch.object(health, "engine", fake_engine), \
         patch("redis.asyncio.from_url", return_value=fake_redis), \
         patch("asyncio.open_connection", fake_open_connection), \
         patch("asyncio.wait_for", AsyncMock(side_effect=lambda coro, timeout: coro if not asyncio.iscoroutine(coro) else coro)):
        # Replace wait_for with a passthrough that awaits the coroutine
        async def passthrough(coro, timeout):
            return await coro
        with patch("asyncio.wait_for", passthrough):
            out = await health.health_deep({"key_id": "t"})

    assert out["services"]["database"] == "connected"
    assert out["services"]["redis"] == "connected"
    assert out["services"]["foxmq"] == "connected"
    assert "agents" in out["database_tables"]
    assert out["status"] in ("healthy", "degraded")


@pytest.mark.asyncio
async def test_health_deep_all_red():
    # DB fails
    fake_engine_ctx = MagicMock()
    fake_engine_ctx.__aenter__ = AsyncMock(side_effect=RuntimeError("db down"))
    fake_engine_ctx.__aexit__ = AsyncMock(return_value=None)

    fake_engine = MagicMock()
    fake_engine.connect = MagicMock(return_value=fake_engine_ctx)

    with patch.object(health, "engine", fake_engine), \
         patch("redis.asyncio.from_url", side_effect=RuntimeError("redis down")), \
         patch("asyncio.open_connection", side_effect=RuntimeError("net down")):
        out = await health.health_deep({"key_id": "t"})

    assert "error" in out["services"]["database"]
    assert "error" in out["services"]["redis"]
    assert "error" in out["services"]["foxmq"]
    assert out["status"] == "degraded"
