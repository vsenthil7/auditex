"""
Auditex -- Vertex consensus client (STUB -- Phase 5).

STUB MODE: Tashi Vertex infrastructure is not yet deployed.
This stub produces REAL cryptographic values using local computation:
  - event_hash: real SHA-256 of the event payload (deterministic, tamper-evident)
  - round:      real incrementing counter stored in Redis (atomic INCR)
  - finalised_at: real UTC timestamp

The stub is HONEST:
  - is_stub=True is always set on the receipt
  - Every call logs "VERTEX_STUB: event finalised"
  - The stub never claims to have achieved distributed BFT consensus

When real Vertex is available (Phase 6+), replace ONLY this file:
  - Submit event_payload to the FoxMQ/Vertex pipeline
  - Poll for consensus confirmation (round number assignment)
  - Return VertexReceipt with is_stub=False
  - The VertexReceipt dataclass and submit_event signature stay identical

DESIGN CONTRACT:
  submit_event(event_payload: dict) -> VertexReceipt
"""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Stub flag -- will be False when real Vertex client is wired up
_STUB_MODE = True

# Redis key for the atomic round counter
_ROUND_COUNTER_KEY = "vertex:round_counter"

# Module-level fallback counter (used only if Redis is unavailable)
_local_round_counter: int = 0


@dataclass
class VertexReceipt:
    """
    Receipt returned by Vertex after event finalisation.

    Fields:
        event_hash:    SHA-256 hex string of the event payload (64 chars).
        round:         Vertex consensus round number (integer >= 1).
        finalised_at:  ISO 8601 UTC timestamp of finalisation.
        is_stub:       True if produced by the stub (no real BFT consensus).
    """
    event_hash: str
    round: int
    finalised_at: str
    is_stub: bool


def submit_event(event_payload: dict) -> VertexReceipt:
    """
    Submit a task event to Vertex for consensus finalisation.

    STUB:
      - Computes real SHA-256 of the event payload
      - Increments Redis counter for real monotonic round number
      - Returns VertexReceipt with is_stub=True

    Real implementation (Phase 6+):
      - Publishes to Vertex via FoxMQ
      - Polls Vertex API for consensus confirmation
      - Returns VertexReceipt with real BFT round number and is_stub=False

    Args:
        event_payload: The canonical event dict from event_builder.

    Returns:
        VertexReceipt with event_hash, round, finalised_at, is_stub.

    Raises:
        VertexSubmitError: If submission or consensus fails (not raised in stub).
    """
    if _STUB_MODE:
        # --- Compute real SHA-256 event hash ---
        serialised = json.dumps(event_payload, sort_keys=True, separators=(",", ":"))
        event_hash = hashlib.sha256(serialised.encode("utf-8")).hexdigest()

        # --- Increment Redis round counter (atomic) ---
        round_number = _increment_round_counter()

        # --- Real UTC timestamp ---
        finalised_at = datetime.now(timezone.utc).isoformat()

        logger.info(
            "VERTEX_STUB: event finalised | hash=%s... round=%d",
            event_hash[:16], round_number,
        )

        return VertexReceipt(
            event_hash=event_hash,
            round=round_number,
            finalised_at=finalised_at,
            is_stub=True,
        )

    # --- Real implementation placeholder (Phase 6+) ---
    # from app.config import settings
    # vertex_api = VertexAPI(settings.VERTEX_NODE_URL, settings.VERTEX_PRIVATE_KEY)
    # submission = vertex_api.submit(event_payload)
    # receipt = vertex_api.poll_confirmation(submission.event_id, timeout=10)
    # return VertexReceipt(
    #     event_hash=receipt.event_hash,
    #     round=receipt.consensus_round,
    #     finalised_at=receipt.finalised_at,
    #     is_stub=False,
    # )

    raise NotImplementedError("Real Vertex client not yet implemented (Phase 6+)")


def _increment_round_counter() -> int:
    """
    Atomically increment the Vertex round counter in Redis.
    Returns the new round number (starts at 1 on first call).

    Falls back to a process-local counter if Redis is unavailable.
    This ensures the stub never blocks task completion due to Redis issues.
    """
    global _local_round_counter

    try:
        import redis as redis_lib
        from app.config import settings

        r = redis_lib.from_url(settings.REDIS_URL, decode_responses=True)
        round_number = r.incr(_ROUND_COUNTER_KEY)
        return int(round_number)

    except Exception as exc:
        # Fallback: use a process-local counter (not persistent across restarts)
        # This is acceptable in stub mode -- round numbers are not BFT-verified
        logger.warning(
            "VERTEX_STUB: Redis unavailable for round counter (%s), using local fallback",
            exc,
        )
        _local_round_counter += 1
        return _local_round_counter


class VertexSubmitError(Exception):
    """Raised when Vertex event submission or consensus fails in real mode."""
