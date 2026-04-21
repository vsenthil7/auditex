"""
Auditex -- Export Signer (Phase 11 Item 1).

Signs and verifies EU AI Act compliance exports with HMAC-SHA256.

Why HMAC-SHA256 (and not RSA / Ed25519):
  - Hackathon scope: symmetric is far simpler to key-manage in docker-compose.
  - EU AI Act Article 12 and Article 17 care about INTEGRITY + NON-REPUDIATION
    across trust boundaries. HMAC covers integrity today; the hook to upgrade
    to asymmetric signing later is isolated to sign_export / verify_signature.
  - ``cryptography.hmac`` uses constant-time comparison via ``h.verify()`` so
    we are resistant to timing attacks.

Canonicalisation:
  - json.dumps(sort_keys=True, separators=(",", ":"), ensure_ascii=False)
  - Stable across dict reorderings: {"a":1,"b":2} and {"b":2,"a":1} produce
    the same signature. ensure_ascii=False keeps non-ASCII intact and still
    reproducible via utf-8 encoding.

Key config:
  - Preferred: EXPORT_SIGNING_KEYS = "id1:hex1,id2:hex2,..."
      * First entry is the ACTIVE signing key.
      * ALL entries are valid for verification (supports key rotation).
  - Legacy fallback: EXPORT_SIGNING_KEY_ID + EXPORT_SIGNING_KEY_HEX.

Public API:
  - canonicalise(payload) -> bytes
  - sign_export(payload) -> dict
  - verify_signature(payload, signature_hex, signing_key_id) -> bool
  - current_key_id() -> str
  - load_keys() -> dict[str, bytes]

Errors:
  - SigningKeyNotConfigured: no usable key in env.
  - UnknownKeyId: verify called with a key_id not in the keyring.
  - SignatureMismatch: signature doesn't match payload for that key_id.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, hmac

from app.config import settings

ALGORITHM = "HMAC-SHA256"
SIGNATURE_SCHEMA_VERSION = "auditex_signed_export_v1"


class ExportSignerError(Exception):
    """Base error for all export signer failures."""


class SigningKeyNotConfigured(ExportSignerError):
    """Raised when no signing key is present in the environment."""


class UnknownKeyId(ExportSignerError):
    """Raised when verification is attempted with an unknown key id."""


class SignatureMismatch(ExportSignerError):
    """Raised when a signature fails HMAC verification."""


# --------------------------------------------------------------------------- #
# Key loading
# --------------------------------------------------------------------------- #
def load_keys() -> dict[str, bytes]:
    """
    Return the keyring as {key_id: raw_bytes}.

    - Multi-key mode: settings.EXPORT_SIGNING_KEYS, comma-separated "id:hex".
    - Legacy single-key mode: EXPORT_SIGNING_KEY_ID + EXPORT_SIGNING_KEY_HEX.

    Raises SigningKeyNotConfigured if neither path produces a valid key.
    """
    raw = (settings.EXPORT_SIGNING_KEYS or "").strip()
    keys: dict[str, bytes] = {}

    if raw:
        for entry in raw.split(","):
            entry = entry.strip()
            if not entry:
                continue
            if ":" not in entry:
                raise SigningKeyNotConfigured(
                    f"EXPORT_SIGNING_KEYS entry missing ':' separator: {entry!r}"
                )
            key_id, hex_key = entry.split(":", 1)
            key_id = key_id.strip()
            hex_key = hex_key.strip()
            if not key_id or not hex_key:
                raise SigningKeyNotConfigured(
                    f"EXPORT_SIGNING_KEYS entry has empty id or key: {entry!r}"
                )
            try:
                keys[key_id] = bytes.fromhex(hex_key)
            except ValueError as exc:
                raise SigningKeyNotConfigured(
                    f"EXPORT_SIGNING_KEYS entry {key_id!r} has invalid hex"
                ) from exc

    if not keys:
        # Legacy single-key fallback
        key_id = (settings.EXPORT_SIGNING_KEY_ID or "").strip()
        hex_key = (settings.EXPORT_SIGNING_KEY_HEX or "").strip()
        if not key_id or not hex_key:
            raise SigningKeyNotConfigured(
                "No signing key configured. Set EXPORT_SIGNING_KEYS or both "
                "EXPORT_SIGNING_KEY_ID and EXPORT_SIGNING_KEY_HEX."
            )
        try:
            keys[key_id] = bytes.fromhex(hex_key)
        except ValueError as exc:
            raise SigningKeyNotConfigured(
                "EXPORT_SIGNING_KEY_HEX is not valid hex"
            ) from exc

    return keys


def current_key_id() -> str:
    """
    Return the ACTIVE signing key id.

    Multi-key mode: first entry in EXPORT_SIGNING_KEYS.
    Legacy mode: EXPORT_SIGNING_KEY_ID.
    """
    raw = (settings.EXPORT_SIGNING_KEYS or "").strip()
    if raw:
        first = raw.split(",")[0].strip()
        if ":" in first:
            kid = first.split(":", 1)[0].strip()
            if kid:
                return kid
    legacy = (settings.EXPORT_SIGNING_KEY_ID or "").strip()
    if not legacy:
        raise SigningKeyNotConfigured(
            "Cannot determine current signing key id -- no key configured."
        )
    return legacy


# --------------------------------------------------------------------------- #
# Canonicalisation + HMAC primitives
# --------------------------------------------------------------------------- #
def canonicalise(payload: dict[str, Any]) -> bytes:
    """
    Deterministic UTF-8 byte encoding of a JSON-serialisable dict.

    Sorted keys + compact separators + ensure_ascii=False.
    Dict reorderings produce identical bytes; any content change does not.
    """
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _hmac_hex(key: bytes, message: bytes) -> str:
    h = hmac.HMAC(key, hashes.SHA256())
    h.update(message)
    return h.finalize().hex()


# --------------------------------------------------------------------------- #
# Public sign / verify
# --------------------------------------------------------------------------- #
def sign_export(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Sign a payload with the ACTIVE key. Returns a signed envelope:

        {
          "schema": "auditex_signed_export_v1",
          "payload": <original payload>,
          "signature": {
              "algorithm": "HMAC-SHA256",
              "signing_key_id": "<id>",
              "signed_at": "<iso-utc>",
              "signature_hex": "<64-char hex>",
          }
        }

    The payload inside the envelope is NOT mutated.

    Raises SigningKeyNotConfigured if no key is available.
    Raises TypeError if payload is not JSON-serialisable.
    """
    keys = load_keys()
    key_id = current_key_id()
    if key_id not in keys:
        # Defensive: load_keys + current_key_id can diverge only if env is
        # mutated between calls. Treat as misconfiguration.
        raise SigningKeyNotConfigured(
            f"Active key id {key_id!r} not found in loaded keyring."
        )

    message = canonicalise(payload)
    signature_hex = _hmac_hex(keys[key_id], message)
    signed_at = datetime.now(timezone.utc).isoformat()

    return {
        "schema": SIGNATURE_SCHEMA_VERSION,
        "payload": payload,
        "signature": {
            "algorithm": ALGORITHM,
            "signing_key_id": key_id,
            "signed_at": signed_at,
            "signature_hex": signature_hex,
        },
    }


def verify_signature(
    payload: dict[str, Any],
    signature_hex: str,
    signing_key_id: str,
) -> bool:
    """
    Verify signature_hex against payload using the key registered under
    signing_key_id.

    Returns True on success. Raises SignatureMismatch if verification fails.
    Raises UnknownKeyId if signing_key_id is not in the keyring.
    Raises SigningKeyNotConfigured if no keys are loadable.
    """
    keys = load_keys()
    if signing_key_id not in keys:
        raise UnknownKeyId(
            f"Signing key id {signing_key_id!r} not in keyring."
        )

    try:
        expected = bytes.fromhex(signature_hex)
    except ValueError as exc:
        raise SignatureMismatch("signature_hex is not valid hex") from exc

    message = canonicalise(payload)
    h = hmac.HMAC(keys[signing_key_id], hashes.SHA256())
    h.update(message)
    try:
        h.verify(expected)
    except InvalidSignature as exc:
        raise SignatureMismatch(
            f"HMAC verify failed for key_id={signing_key_id!r}"
        ) from exc
    return True
