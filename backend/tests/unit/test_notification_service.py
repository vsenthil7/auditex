"""Tests for services.notification_service."""
from __future__ import annotations

import hashlib
import hmac
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from services import notification_service
from services.notification_service import (
    SIGNATURE_HEADER, EVENT_TYPE_HEADER,
    deliver, sign_payload, verify_signature,
)

SECRET = "ab" * 32


def test_sign_payload_matches_manual_hmac():
    payload = {"a": 1, "b": "x"}
    sig = sign_payload(payload, SECRET)
    # Manual replication
    from core.reporting.export_signer import canonicalise
    expected = hmac.new(bytes.fromhex(SECRET), canonicalise(payload), hashlib.sha256).hexdigest()
    assert sig == expected
    assert len(sig) == 64


def test_sign_payload_rejects_bad_hex():
    with pytest.raises(ValueError):
        sign_payload({"x": 1}, "nothex")


def test_verify_signature_happy_path():
    payload = {"k": "v"}
    sig = sign_payload(payload, SECRET)
    assert verify_signature(payload, sig, SECRET) is True


def test_verify_signature_case_insensitive():
    payload = {"k": "v"}
    sig = sign_payload(payload, SECRET).upper()
    assert verify_signature(payload, sig, SECRET) is True


def test_verify_signature_rejects_mismatch():
    assert verify_signature({"k": "v"}, "aa" * 32, SECRET) is False


def test_verify_signature_rejects_empty_sig():
    assert verify_signature({"k": "v"}, "", SECRET) is False


def test_verify_signature_rejects_bad_secret_hex():
    # Bad secret triggers ValueError inside sign_payload -> returns False
    assert verify_signature({"k": "v"}, "ab" * 32, "nothex") is False


class _FakeAsyncClient:
    """Context-manager stub for httpx.AsyncClient."""
    def __init__(self, post_result=None, raise_exc=None):
        self._result = post_result
        self._raise = raise_exc
    async def __aenter__(self):
        return self
    async def __aexit__(self, exc_type, exc, tb):
        return None
    async def post(self, url, content=None, headers=None):
        if self._raise is not None:
            raise self._raise
        return self._result


def _make_response(status_code, body="ok"):
    r = MagicMock()
    r.status_code = status_code
    r.text = body
    return r


@pytest.mark.asyncio
async def test_deliver_success_2xx_returns_delivered():
    resp = _make_response(200, "ok body")
    with patch.object(notification_service.httpx, "AsyncClient", return_value=_FakeAsyncClient(post_result=resp)):
        status_str, resp_status, resp_body, sig = await deliver(
            url="https://e.com", event_type="task.completed",
            payload={"a": 1}, secret_hex=SECRET,
        )
    assert status_str == "DELIVERED"
    assert resp_status == 200
    assert resp_body == "ok body"
    assert len(sig) == 64


@pytest.mark.asyncio
async def test_deliver_non_2xx_returns_failed():
    resp = _make_response(500, "server err")
    with patch.object(notification_service.httpx, "AsyncClient", return_value=_FakeAsyncClient(post_result=resp)):
        status_str, resp_status, resp_body, sig = await deliver(
            url="https://e.com", event_type="e",
            payload={"a": 1}, secret_hex=SECRET,
        )
    assert status_str == "FAILED"
    assert resp_status == 500


@pytest.mark.asyncio
async def test_deliver_timeout_returns_timeout():
    with patch.object(notification_service.httpx, "AsyncClient", return_value=_FakeAsyncClient(raise_exc=httpx.TimeoutException("slow"))):
        status_str, resp_status, resp_body, sig = await deliver(
            url="https://e.com", event_type="e",
            payload={"a": 1}, secret_hex=SECRET,
        )
    assert status_str == "TIMEOUT"
    assert resp_status is None
    assert resp_body is None


@pytest.mark.asyncio
async def test_deliver_http_error_returns_transport_error():
    with patch.object(notification_service.httpx, "AsyncClient", return_value=_FakeAsyncClient(raise_exc=httpx.ConnectError("refused"))):
        status_str, resp_status, resp_body, sig = await deliver(
            url="https://e.com", event_type="e",
            payload={"a": 1}, secret_hex=SECRET,
        )
    assert status_str == "TRANSPORT_ERROR"
    assert resp_status is None
    assert "refused" in resp_body


@pytest.mark.asyncio
async def test_deliver_empty_response_body():
    resp = _make_response(204, "")
    with patch.object(notification_service.httpx, "AsyncClient", return_value=_FakeAsyncClient(post_result=resp)):
        status_str, _, body, _ = await deliver(
            url="https://e.com", event_type="e",
            payload={"a": 1}, secret_hex=SECRET,
        )
    assert status_str == "DELIVERED"
    assert body is None


def test_header_constants():
    assert SIGNATURE_HEADER == "X-Auditex-Signature"
    assert EVENT_TYPE_HEADER == "X-Auditex-Event"
