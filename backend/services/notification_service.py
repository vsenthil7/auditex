"""Auditex -- Webhook notification service (Phase 11 Item 6).

Signs payloads with HMAC-SHA256 using the subscription secret and POSTs them
to subscriber URLs. Persists both the delivery record and the result.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
from typing import Any

import httpx

from core.reporting.export_signer import canonicalise

logger = logging.getLogger(__name__)

SIGNATURE_HEADER = "X-Auditex-Signature"
EVENT_TYPE_HEADER = "X-Auditex-Event"
DEFAULT_TIMEOUT_SECS = 10.0


def sign_payload(payload: dict[str, Any], secret_hex: str) -> str:
    """Compute HMAC-SHA256 of the canonical JSON, return hex digest."""
    try:
        key = bytes.fromhex(secret_hex)
    except ValueError as exc:
        raise ValueError(f"secret_hex is not valid hex: {exc}") from exc
    canonical = canonicalise(payload)
    return hmac.new(key, canonical, hashlib.sha256).hexdigest()


async def deliver(
    url: str, event_type: str, payload: dict[str, Any], secret_hex: str,
    *, timeout_secs: float = DEFAULT_TIMEOUT_SECS,
) -> tuple[str, int | None, str | None, str]:
    """POST a signed payload. Returns (status, response_status, response_body, signature_hex)."""
    signature_hex = sign_payload(payload, secret_hex)
    headers = {
        "Content-Type": "application/json",
        SIGNATURE_HEADER: signature_hex,
        EVENT_TYPE_HEADER: event_type,
    }
    body = canonicalise(payload)
    try:
        async with httpx.AsyncClient(timeout=timeout_secs) as client:
            response = await client.post(url, content=body, headers=headers)
    except httpx.TimeoutException:
        logger.warning("webhook timeout url=%s event=%s", url, event_type)
        return ("TIMEOUT", None, None, signature_hex)
    except httpx.HTTPError as exc:
        logger.warning("webhook transport error url=%s err=%s", url, exc)
        return ("TRANSPORT_ERROR", None, str(exc)[:2000], signature_hex)
    body_text = response.text[:2000] if response.text else None
    if 200 <= response.status_code < 300:
        return ("DELIVERED", response.status_code, body_text, signature_hex)
    return ("FAILED", response.status_code, body_text, signature_hex)


def verify_signature(payload: dict[str, Any], signature_hex: str, secret_hex: str) -> bool:
    """Constant-time signature verification for consumer-side testing."""
    try:
        expected = sign_payload(payload, secret_hex)
    except ValueError:
        return False
    return hmac.compare_digest(expected.lower(), (signature_hex or "").strip().lower())
