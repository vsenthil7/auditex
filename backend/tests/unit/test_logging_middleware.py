"""Tests for app.api.middleware.logging."""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.middleware import logging as log_mw
from app.api.middleware.logging import (
    JSONLoggingMiddleware,
    _build_log_record,
    _identity,
)


def _make_request(api_key=None, client_host="9.9.9.9", path="/p", query="", ua="ua", req_id=None, method="GET"):
    req = MagicMock()
    req.method = method
    headers = MagicMock()
    def hget(k, default=None):
        if k == "X-API-Key" and api_key:
            return api_key
        if k == "X-Request-ID":
            return req_id
        if k == "user-agent":
            return ua
        return default
    headers.get = hget
    req.headers = headers
    if client_host is None:
        req.client = None
    else:
        c = MagicMock(); c.host = client_host
        req.client = c
    url = MagicMock(); url.path = path; url.query = query
    req.url = url
    return req


# -------------------------------------------------------------
# _identity
# -------------------------------------------------------------
def test_identity_api_key_wins():
    assert _identity(_make_request(api_key="ABC")) == "k:ABC"


def test_identity_client_host_fallback():
    assert _identity(_make_request(api_key=None, client_host="1.1.1.1")) == "ip:1.1.1.1"


def test_identity_unknown_when_no_client():
    assert _identity(_make_request(api_key=None, client_host=None)) == "ip:unknown"


# -------------------------------------------------------------
# _build_log_record
# -------------------------------------------------------------
def test_build_log_record_shape():
    line = _build_log_record("r1", "GET", "/x", "a=1", 200, 42, "k:key", "curl")
    d = json.loads(line)
    assert d["request_id"] == "r1"
    assert d["method"] == "GET"
    assert d["path"] == "/x"
    assert d["query"] == "a=1"
    assert d["status"] == 200
    assert d["duration_ms"] == 42
    assert d["identity"] == "k:key"
    assert d["user_agent"] == "curl"


def test_build_log_record_empty_query_is_blank():
    line = _build_log_record("r", "GET", "/", "", 200, 1, "ip:x", "")
    d = json.loads(line)
    assert d["query"] == ""


# -------------------------------------------------------------
# JSONLoggingMiddleware.dispatch
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_dispatch_2xx_logs_info_and_sets_header():
    mw = JSONLoggingMiddleware(app=None)
    req = _make_request()
    resp = MagicMock(); resp.headers = {}; resp.status_code = 200
    call_next = AsyncMock(return_value=resp)
    with patch.object(log_mw.logger, "info") as mk_info:
        out = await mw.dispatch(req, call_next)
    mk_info.assert_called_once()
    assert out is resp
    assert "X-Request-ID" in out.headers
    assert len(out.headers["X-Request-ID"]) > 0


@pytest.mark.asyncio
async def test_dispatch_honours_incoming_request_id():
    mw = JSONLoggingMiddleware(app=None)
    req = _make_request(req_id="external-id-123")
    resp = MagicMock(); resp.headers = {}; resp.status_code = 200
    call_next = AsyncMock(return_value=resp)
    with patch.object(log_mw.logger, "info"):
        out = await mw.dispatch(req, call_next)
    assert out.headers["X-Request-ID"] == "external-id-123"


@pytest.mark.asyncio
async def test_dispatch_4xx_logs_warning():
    mw = JSONLoggingMiddleware(app=None)
    req = _make_request()
    resp = MagicMock(); resp.headers = {}; resp.status_code = 404
    call_next = AsyncMock(return_value=resp)
    with patch.object(log_mw.logger, "warning") as mk_w, patch.object(log_mw.logger, "info") as mk_i:
        await mw.dispatch(req, call_next)
    mk_w.assert_called_once()
    mk_i.assert_not_called()


@pytest.mark.asyncio
async def test_dispatch_5xx_logs_error():
    mw = JSONLoggingMiddleware(app=None)
    req = _make_request()
    resp = MagicMock(); resp.headers = {}; resp.status_code = 503
    call_next = AsyncMock(return_value=resp)
    with patch.object(log_mw.logger, "error") as mk_e, patch.object(log_mw.logger, "info") as mk_i:
        await mw.dispatch(req, call_next)
    mk_e.assert_called_once()
    mk_i.assert_not_called()


@pytest.mark.asyncio
async def test_dispatch_exception_logs_error_and_reraises():
    mw = JSONLoggingMiddleware(app=None)
    req = _make_request()
    call_next = AsyncMock(side_effect=RuntimeError("boom"))
    with patch.object(log_mw.logger, "error") as mk_e:
        with pytest.raises(RuntimeError):
            await mw.dispatch(req, call_next)
    mk_e.assert_called_once()
    # Verify the logged payload has status 500
    logged = mk_e.call_args.args[0]
    import json as _json
    d = _json.loads(logged)
    assert d["status"] == 500


@pytest.mark.asyncio
async def test_dispatch_log_contains_method_and_path():
    mw = JSONLoggingMiddleware(app=None)
    req = _make_request(method="POST", path="/api/v1/tasks", query="x=1")
    resp = MagicMock(); resp.headers = {}; resp.status_code = 201
    call_next = AsyncMock(return_value=resp)
    with patch.object(log_mw.logger, "info") as mk_i:
        await mw.dispatch(req, call_next)
    logged = mk_i.call_args.args[0]
    import json as _json
    d = _json.loads(logged)
    assert d["method"] == "POST"
    assert d["path"] == "/api/v1/tasks"
    assert d["query"] == "x=1"
    assert d["status"] == 201
