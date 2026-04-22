"""Tests for core.consensus.proof_verifier."""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from core.consensus import proof_verifier
from core.consensus.proof_verifier import (
    EmptyEventChain,
    ProofVerifierError,
    VerificationResult,
    _event_to_dict,
    compute_chain_hash,
    verify_task_proof,
)
from core.reporting.export_signer import canonicalise


# -------------------------------------------------------------
# _event_to_dict
# -------------------------------------------------------------
def test_event_to_dict_passes_dict_through():
    d = {"a": 1, "b": [2, 3]}
    assert _event_to_dict(d) is d


def test_event_to_dict_orm_with_datetime_and_uuid():
    mock = MagicMock(spec=["id", "task_id", "event_type", "payload_json", "created_at"])
    mock.id = uuid.uuid4()
    mock.task_id = uuid.uuid4()
    mock.event_type = "TASK_SUBMITTED"
    mock.payload_json = {"nested": "dict"}
    mock.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    out = _event_to_dict(mock)
    assert out["event_type"] == "TASK_SUBMITTED"
    assert out["payload_json"] == {"nested": "dict"}
    assert out["created_at"] == "2026-01-01T00:00:00+00:00"
    assert isinstance(out["id"], str)
    assert isinstance(out["task_id"], str)


def test_event_to_dict_skips_none_attrs():
    class E:
        id = None
        task_id = None
        event_type = "X"
        payload_json = None
        created_at = None
    out = _event_to_dict(E())
    assert out == {"event_type": "X"}


def test_event_to_dict_non_standard_type_is_stringified():
    class Weird:
        def __str__(self):
            return "weird-repr"
    class E:
        id = Weird()
        task_id = None
        event_type = None
        payload_json = None
        created_at = None
    out = _event_to_dict(E())
    assert out["id"] == "weird-repr"


# -------------------------------------------------------------
# compute_chain_hash
# -------------------------------------------------------------
def test_compute_chain_hash_single_event():
    ev = {"event_type": "SUBMITTED", "n": 1}
    h = compute_chain_hash([ev])
    expected = hashlib.sha256(canonicalise(ev)).hexdigest()
    assert h == expected
    assert len(h) == 64


def test_compute_chain_hash_multiple_events_rolling():
    e1 = {"t": 1}
    e2 = {"t": 2}
    e3 = {"t": 3}
    h = compute_chain_hash([e1, e2, e3])
    manual = hashlib.sha256(canonicalise(e1)).digest()
    manual = hashlib.sha256(manual + canonicalise(e2)).digest()
    manual = hashlib.sha256(manual + canonicalise(e3)).digest()
    assert h == manual.hex()


def test_compute_chain_hash_empty_raises():
    with pytest.raises(EmptyEventChain):
        compute_chain_hash([])


# -------------------------------------------------------------
# verify_task_proof
# -------------------------------------------------------------
def test_verify_task_proof_matches():
    ev = {"e": "ok"}
    expected = compute_chain_hash([ev])
    result = verify_task_proof([ev], expected)
    assert result.verified is True
    assert result.event_count == 1
    assert result.reason is None
    assert result.expected_hash == expected
    assert result.computed_hash == expected


def test_verify_task_proof_case_insensitive_match():
    ev = {"e": "ok"}
    computed = compute_chain_hash([ev])
    result = verify_task_proof([ev], computed.upper())
    assert result.verified is True


def test_verify_task_proof_mismatch():
    ev = {"e": "ok"}
    result = verify_task_proof([ev], "ab" * 32)
    assert result.verified is False
    assert "does not match" in result.reason
    assert result.event_count == 1


def test_verify_task_proof_empty_expected():
    ev = {"e": "ok"}
    result = verify_task_proof([ev], "")
    assert result.verified is False
    assert result.reason == "expected_hash is empty"


def test_verify_task_proof_none_expected():
    ev = {"e": "ok"}
    result = verify_task_proof([ev], None)
    assert result.verified is False
    assert result.reason == "expected_hash is empty"


def test_verify_task_proof_empty_events_raises():
    with pytest.raises(EmptyEventChain):
        verify_task_proof([], "ab" * 32)


def test_verification_result_is_frozen_dataclass():
    r = VerificationResult(True, "a", "a", 1, None)
    with pytest.raises(Exception):
        r.verified = False


def test_proof_verifier_error_hierarchy():
    assert issubclass(EmptyEventChain, ProofVerifierError)
    assert issubclass(ProofVerifierError, Exception)


def test_module_has_expected_public_api():
    for name in ("verify_task_proof", "compute_chain_hash", "VerificationResult", "EmptyEventChain", "ProofVerifierError"):
        assert hasattr(proof_verifier, name)
