"""Auditex Proof Verifier (Phase 11 Item 2). Independently verifies the Vertex event-chain proof attached to a completed task."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Iterable

from core.reporting.export_signer import canonicalise


@dataclass(frozen=True)
class VerificationResult:
    """Outcome of a third-party proof verification."""
    verified: bool
    expected_hash: str
    computed_hash: str
    event_count: int
    reason: str | None = None


class ProofVerifierError(Exception):
    """Base error for proof_verifier failures."""


class EmptyEventChain(ProofVerifierError):
    """Raised when the event list is empty -- cannot verify nothing."""


def _event_to_dict(event: Any) -> dict:
    """Normalise an Event ORM object OR dict to a plain dict for canonical hashing."""
    if isinstance(event, dict):
        return event
    out: dict = {}
    for attr in ("id", "task_id", "event_type", "payload_json", "created_at"):
        val = getattr(event, attr, None)
        if val is None:
            continue
        if hasattr(val, "isoformat"):
            out[attr] = val.isoformat()
        elif isinstance(val, (str, int, float, bool, list, dict)):
            out[attr] = val
        else:
            out[attr] = str(val)
    return out


def compute_chain_hash(events: Iterable[Any]) -> str:
    """Rolling sha256 chain hash over an ordered event sequence."""
    event_list = list(events)
    if not event_list:
        raise EmptyEventChain("Cannot compute chain hash over empty event list.")
    running = b""
    for i, ev in enumerate(event_list):
        canonical = canonicalise(_event_to_dict(ev))
        if i == 0:
            running = hashlib.sha256(canonical).digest()
        else:
            running = hashlib.sha256(running + canonical).digest()
    return running.hex()


def verify_task_proof(events: Iterable[Any], expected_hash: str) -> VerificationResult:
    """Verify that the chain hash of events matches expected_hash. Case-insensitive."""
    event_list = list(events)
    computed = compute_chain_hash(event_list)
    normalised_expected = (expected_hash or "").strip().lower()
    normalised_computed = computed.strip().lower()

    if not normalised_expected:
        return VerificationResult(
            verified=False,
            expected_hash=expected_hash or "",
            computed_hash=computed,
            event_count=len(event_list),
            reason="expected_hash is empty",
        )

    if normalised_expected == normalised_computed:
        return VerificationResult(
            verified=True,
            expected_hash=expected_hash,
            computed_hash=computed,
            event_count=len(event_list),
            reason=None,
        )

    return VerificationResult(
        verified=False,
        expected_hash=expected_hash,
        computed_hash=computed,
        event_count=len(event_list),
        reason="chain hash does not match expected hash (tampered or wrong events)",
    )
