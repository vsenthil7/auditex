"""
Auditex -- Consensus evaluator.
Pure function: given a list of verdict strings, returns the consensus label.

Rules (2/3 majority = PASS, per spec):
  3 APPROVE -> "3_OF_3_APPROVE"
  2 APPROVE -> "2_OF_3_APPROVE"
  1 APPROVE -> "1_OF_3_APPROVE"  (FAIL -- escalate in Phase 5)
  0 APPROVE -> "0_OF_3_APPROVE"  (FAIL -- escalate in Phase 5)

Phase 4 returns the result string.
Escalation routing is Phase 5.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# Consensus strings -- used directly in the review result JSON
_CONSENSUS_3_OF_3 = "3_OF_3_APPROVE"
_CONSENSUS_2_OF_3 = "2_OF_3_APPROVE"
_CONSENSUS_1_OF_3 = "1_OF_3_APPROVE"
_CONSENSUS_0_OF_3 = "0_OF_3_APPROVE"

# Mapping from approve count to label (for exactly 3 reviewers)
_LABELS = {
    3: _CONSENSUS_3_OF_3,
    2: _CONSENSUS_2_OF_3,
    1: _CONSENSUS_1_OF_3,
    0: _CONSENSUS_0_OF_3,
}


def evaluate_consensus(verdicts: list[str]) -> str:
    """
    Evaluate the consensus from a list of reviewer verdict strings.

    Args:
        verdicts: List of verdict strings, each "APPROVE" or "REJECT".
                  Expected to contain exactly 3 entries (one per reviewer).

    Returns:
        One of: "3_OF_3_APPROVE", "2_OF_3_APPROVE",
                "1_OF_3_APPROVE", "0_OF_3_APPROVE"

    Raises:
        ValueError if the verdicts list is empty or contains invalid values.
    """
    if not verdicts:
        raise ValueError("evaluate_consensus: verdicts list is empty")

    normalised = [v.upper().strip() for v in verdicts]
    invalid = [v for v in normalised if v not in ("APPROVE", "REJECT")]
    if invalid:
        raise ValueError(
            f"evaluate_consensus: invalid verdict values: {invalid}"
        )

    approve_count = sum(1 for v in normalised if v == "APPROVE")
    total = len(normalised)

    # For the standard 3-reviewer case use the pre-defined labels
    if total == 3:
        label = _LABELS[approve_count]
    else:
        # Generalised label for non-standard reviewer counts
        label = f"{approve_count}_OF_{total}_APPROVE"

    # 2+ of 3 = PASS; fewer = requires escalation (Phase 5)
    passed = approve_count >= 2

    logger.info(
        "evaluate_consensus: approve=%d/%d label=%s passed=%s",
        approve_count, total, label, passed,
    )

    return label


def is_consensus_passed(consensus_label: str) -> bool:
    """
    Return True if the consensus label represents a passing result (2+ of 3 approve).

    Args:
        consensus_label: The string returned by evaluate_consensus().

    Returns:
        True if 2 or more reviewers approved.
    """
    return consensus_label in (_CONSENSUS_2_OF_3, _CONSENSUS_3_OF_3)
