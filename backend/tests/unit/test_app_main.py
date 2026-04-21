"""Tests for app.main (FastAPI app factory + lifespan)."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def test_app_importable():
    from app.main import app
    assert app.title == "Auditex"


def test_app_has_routers_registered():
    from app.main import app
    routes = {r.path for r in app.routes}
    # Root redirect
    assert "/" in routes
    # At least one v1 route from each router
    v1_paths = [p for p in routes if p.startswith("/api/v1/")]
    assert any("tasks" in p for p in v1_paths)
    assert any("health" in p for p in v1_paths)
    assert any("agents" in p for p in v1_paths)
    assert any("reports" in p for p in v1_paths)


@pytest.mark.asyncio
async def test_root_endpoint_returns_message():
    from app.main import root
    out = await root()
    assert "Auditex" in out["message"]


@pytest.mark.asyncio
async def test_lifespan_happy_path():
    from app.main import app, lifespan
    mock_result = MagicMock(returncode=0, stderr="")
    with patch("subprocess.run", return_value=mock_result):
        async with lifespan(app):
            pass  # just let startup + shutdown both execute


@pytest.mark.asyncio
async def test_lifespan_migration_failure():
    from app.main import app, lifespan
    mock_result = MagicMock(returncode=1, stderr="table already exists")
    with patch("subprocess.run", return_value=mock_result):
        async with lifespan(app):
            pass


@pytest.mark.asyncio
async def test_lifespan_migration_exception():
    from app.main import app, lifespan
    with patch("subprocess.run", side_effect=RuntimeError("subprocess boom")):
        async with lifespan(app):
            pass
