"""
Tests for backend/core/reporting/export_signer.py.

Target: 100% line + branch + statement + function coverage.

All tests manipulate settings via monkeypatch on the live ``settings`` object
from ``app.config``. We do NOT reload app.config here -- export_signer reads
each attribute at call time (not import time), so direct attribute override
is sufficient and avoids polluting other test modules.
"""
from __future__ import annotations

import pytest

from app.config import settings
from core.reporting import export_signer as es


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #
@pytest.fixture
def clean_keys(monkeypatch):
    """Blank out all signing-key env reads so each test starts clean."""
    monkeypatch.setattr(settings, "EXPORT_SIGNING_KEYS", "")
    monkeypatch.setattr(settings, "EXPORT_SIGNING_KEY_ID", "")
    monkeypatch.setattr(settings, "EXPORT_SIGNING_KEY_HEX", "")
    return monkeypatch


@pytest.fixture
def single_key(monkeypatch):
    """Legacy single-key mode."""
    monkeypatch.setattr(settings, "EXPORT_SIGNING_KEYS", "")
    monkeypatch.setattr(settings, "EXPORT_SIGNING_KEY_ID", "test-key-1")
    monkeypatch.setattr(settings, "EXPORT_SIGNING_KEY_HEX", "aa" * 32)
    return monkeypatch


@pytest.fixture
def multi_key(monkeypatch):
    """Multi-key mode: active=k-new, also-valid=k-old."""
    monkeypatch.setattr(
        settings,
        "EXPORT_SIGNING_KEYS",
        "k-new:" + ("bb" * 32) + ",k-old:" + ("cc" * 32),
    )
    # Legacy fields should be ignored when EXPORT_SIGNING_KEYS is set.
    monkeypatch.setattr(settings, "EXPORT_SIGNING_KEY_ID", "legacy-should-be-ignored")
    monkeypatch.setattr(settings, "EXPORT_SIGNING_KEY_HEX", "dd" * 32)
    return monkeypatch


# --------------------------------------------------------------------------- #
# canonicalise
# --------------------------------------------------------------------------- #
def test_canonicalise_sorts_keys():
    a = {"z": 1, "a": 2}
    b = {"a": 2, "z": 1}
    assert es.canonicalise(a) == es.canonicalise(b)


def test_canonicalise_compact_and_utf8():
    # Compact separators -> no whitespace between items
    payload = {"a": 1, "b": [1, 2]}
    raw = es.canonicalise(payload)
    assert b" " not in raw
    assert raw == b'{"a":1,"b":[1,2]}'


def test_canonicalise_unicode_preserved():
    payload = {"msg": "naïve café — EU AI Act"}
    raw = es.canonicalise(payload)
    # Non-ASCII must survive intact (no \u escapes)
    assert "naïve café".encode("utf-8") in raw
    # Round-trip decode works
    assert raw.decode("utf-8").startswith('{"msg":"naïve')


# --------------------------------------------------------------------------- #
# load_keys
# --------------------------------------------------------------------------- #
def test_load_keys_legacy_happy_path(single_key):
    keys = es.load_keys()
    assert keys == {"test-key-1": bytes.fromhex("aa" * 32)}


def test_load_keys_multi_happy_path(multi_key):
    keys = es.load_keys()
    assert set(keys) == {"k-new", "k-old"}
    assert keys["k-new"] == bytes.fromhex("bb" * 32)
    assert keys["k-old"] == bytes.fromhex("cc" * 32)


def test_load_keys_missing_colon_raises(monkeypatch):
    monkeypatch.setattr(settings, "EXPORT_SIGNING_KEYS", "no-colon-here")
    with pytest.raises(es.SigningKeyNotConfigured, match="missing ':'"):
        es.load_keys()


def test_load_keys_empty_id_raises(monkeypatch):
    monkeypatch.setattr(settings, "EXPORT_SIGNING_KEYS", ":" + "aa" * 32)
    with pytest.raises(es.SigningKeyNotConfigured, match="empty id or key"):
        es.load_keys()


def test_load_keys_empty_hex_raises(monkeypatch):
    monkeypatch.setattr(settings, "EXPORT_SIGNING_KEYS", "id:")
    with pytest.raises(es.SigningKeyNotConfigured, match="empty id or key"):
        es.load_keys()


def test_load_keys_invalid_hex_raises(monkeypatch):
    monkeypatch.setattr(settings, "EXPORT_SIGNING_KEYS", "bad-key:zzzznothex")
    with pytest.raises(es.SigningKeyNotConfigured, match="invalid hex"):
        es.load_keys()


def test_load_keys_empty_entry_skipped(monkeypatch):
    # Trailing comma -> empty entry -> must be skipped silently, not raise
    monkeypatch.setattr(
        settings,
        "EXPORT_SIGNING_KEYS",
        "id1:" + ("11" * 32) + ",",
    )
    keys = es.load_keys()
    assert keys == {"id1": bytes.fromhex("11" * 32)}


def test_load_keys_no_key_at_all_raises(clean_keys):
    with pytest.raises(es.SigningKeyNotConfigured, match="No signing key"):
        es.load_keys()


def test_load_keys_legacy_invalid_hex_raises(monkeypatch):
    monkeypatch.setattr(settings, "EXPORT_SIGNING_KEYS", "")
    monkeypatch.setattr(settings, "EXPORT_SIGNING_KEY_ID", "k")
    monkeypatch.setattr(settings, "EXPORT_SIGNING_KEY_HEX", "not-hex")
    with pytest.raises(es.SigningKeyNotConfigured, match="not valid hex"):
        es.load_keys()


# --------------------------------------------------------------------------- #
# current_key_id
# --------------------------------------------------------------------------- #
def test_current_key_id_multi(multi_key):
    assert es.current_key_id() == "k-new"


def test_current_key_id_legacy(single_key):
    assert es.current_key_id() == "test-key-1"


def test_current_key_id_none_raises(clean_keys):
    with pytest.raises(es.SigningKeyNotConfigured):
        es.current_key_id()


def test_current_key_id_malformed_multi_falls_back_to_legacy(monkeypatch):
    # EXPORT_SIGNING_KEYS set but first entry is malformed (no colon) AND
    # legacy EXPORT_SIGNING_KEY_ID exists. current_key_id should fall back.
    monkeypatch.setattr(settings, "EXPORT_SIGNING_KEYS", "malformed-no-colon")
    monkeypatch.setattr(settings, "EXPORT_SIGNING_KEY_ID", "legacy-fallback")
    monkeypatch.setattr(settings, "EXPORT_SIGNING_KEY_HEX", "aa" * 32)
    assert es.current_key_id() == "legacy-fallback"


def test_current_key_id_empty_id_in_multi_falls_back_to_legacy(monkeypatch):
    # First entry has ":" but id portion is whitespace-only
    monkeypatch.setattr(settings, "EXPORT_SIGNING_KEYS", "  :" + "aa" * 32)
    monkeypatch.setattr(settings, "EXPORT_SIGNING_KEY_ID", "legacy2")
    monkeypatch.setattr(settings, "EXPORT_SIGNING_KEY_HEX", "aa" * 32)
    assert es.current_key_id() == "legacy2"


# --------------------------------------------------------------------------- #
# sign_export round-trip
# --------------------------------------------------------------------------- #
def test_sign_export_returns_envelope(single_key):
    payload = {"task_id": "abc", "article_9": {"ok": True}}
    envelope = es.sign_export(payload)
    assert envelope["schema"] == es.SIGNATURE_SCHEMA_VERSION
    assert envelope["payload"] == payload
    assert envelope["signature"]["algorithm"] == "HMAC-SHA256"
    assert envelope["signature"]["signing_key_id"] == "test-key-1"
    assert len(envelope["signature"]["signature_hex"]) == 64
    # signed_at is ISO-8601 and timezone-aware
    assert "+00:00" in envelope["signature"]["signed_at"] or envelope[
        "signature"
    ]["signed_at"].endswith("Z")


def test_sign_export_payload_not_mutated(single_key):
    payload = {"a": 1}
    before = dict(payload)
    es.sign_export(payload)
    assert payload == before


def test_sign_export_reorder_produces_same_signature(single_key):
    p1 = {"a": 1, "b": 2, "c": [3, 4]}
    p2 = {"c": [3, 4], "b": 2, "a": 1}
    sig1 = es.sign_export(p1)["signature"]["signature_hex"]
    sig2 = es.sign_export(p2)["signature"]["signature_hex"]
    assert sig1 == sig2


def test_sign_export_detects_content_change(single_key):
    sig1 = es.sign_export({"a": 1})["signature"]["signature_hex"]
    sig2 = es.sign_export({"a": 2})["signature"]["signature_hex"]
    assert sig1 != sig2


def test_sign_export_no_key_raises(clean_keys):
    with pytest.raises(es.SigningKeyNotConfigured):
        es.sign_export({"a": 1})


def test_sign_export_typeerror_on_nonserialisable(single_key):
    with pytest.raises(TypeError):
        es.sign_export({"bad": object()})


def test_sign_export_active_key_missing_from_keyring_raises(monkeypatch):
    """
    Defensive branch: current_key_id() returns an id that load_keys()
    did not produce. Achievable only by mid-call env mutation; we simulate
    by monkeypatching current_key_id directly.
    """
    monkeypatch.setattr(settings, "EXPORT_SIGNING_KEYS", "id-a:" + ("aa" * 32))
    monkeypatch.setattr(es, "current_key_id", lambda: "id-z-not-in-keyring")
    with pytest.raises(es.SigningKeyNotConfigured, match="not found in loaded keyring"):
        es.sign_export({"a": 1})


# --------------------------------------------------------------------------- #
# verify_signature
# --------------------------------------------------------------------------- #
def test_verify_signature_round_trip(single_key):
    payload = {"x": 1, "y": [2, 3]}
    env = es.sign_export(payload)
    assert es.verify_signature(
        env["payload"],
        env["signature"]["signature_hex"],
        env["signature"]["signing_key_id"],
    ) is True


def test_verify_signature_tampered_payload_raises(single_key):
    payload = {"x": 1}
    env = es.sign_export(payload)
    tampered = {"x": 2}
    with pytest.raises(es.SignatureMismatch, match="HMAC verify failed"):
        es.verify_signature(
            tampered,
            env["signature"]["signature_hex"],
            env["signature"]["signing_key_id"],
        )


def test_verify_signature_wrong_key_raises(multi_key):
    # Sign with k-new, then try to verify with k-old's signature hex (mismatched)
    payload = {"x": 1}
    env = es.sign_export(payload)
    assert env["signature"]["signing_key_id"] == "k-new"
    with pytest.raises(es.SignatureMismatch):
        es.verify_signature(
            payload,
            env["signature"]["signature_hex"],
            "k-old",  # valid key id but different key -> mismatch
        )


def test_verify_signature_unknown_key_id_raises(single_key):
    with pytest.raises(es.UnknownKeyId, match="not in keyring"):
        es.verify_signature({"x": 1}, "00" * 32, "key-that-does-not-exist")


def test_verify_signature_nonhex_signature_raises(single_key):
    with pytest.raises(es.SignatureMismatch, match="not valid hex"):
        es.verify_signature({"x": 1}, "zznothex", "test-key-1")


def test_verify_signature_key_rotation_old_key_still_valid(multi_key):
    """
    Rotation scenario: a signature produced with k-old (previous active)
    must still verify after rotation to k-new as active.
    """
    # Simulate the "old era": switch active to k-old first and sign.
    # Easiest: use legacy fallback with k-old's bytes, sign, then restore
    # multi-key config and verify.
    import copy
    legacy_payload = {"era": "old"}

    # Step 1: sign as if k-old were the active key.
    # Use a minimal single-key setup so active = k-old.
    snapshot_keys = settings.EXPORT_SIGNING_KEYS
    snapshot_id = settings.EXPORT_SIGNING_KEY_ID
    snapshot_hex = settings.EXPORT_SIGNING_KEY_HEX
    try:
        settings.EXPORT_SIGNING_KEYS = ""
        settings.EXPORT_SIGNING_KEY_ID = "k-old"
        settings.EXPORT_SIGNING_KEY_HEX = "cc" * 32
        env_old = es.sign_export(legacy_payload)
        assert env_old["signature"]["signing_key_id"] == "k-old"
    finally:
        settings.EXPORT_SIGNING_KEYS = snapshot_keys
        settings.EXPORT_SIGNING_KEY_ID = snapshot_id
        settings.EXPORT_SIGNING_KEY_HEX = snapshot_hex

    # Step 2: back to multi-key world (active=k-new). Old signature must
    # still verify against k-old in the keyring.
    assert es.verify_signature(
        legacy_payload,
        env_old["signature"]["signature_hex"],
        "k-old",
    ) is True
