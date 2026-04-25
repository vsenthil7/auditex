"""
Auditex - Article 14 Human Oversight policy logic.

Pure functions, no DB / no HTTP / no Celery. Easy to unit-test (HIL-14).

A policy answers four questions per task:
  1. requires_human_oversight(task_type, policy)  -> bool
  2. evaluate_quorum(decisions, policy)            -> QuorumResult
  3. is_timed_out(awaiting_since, policy, now)     -> bool
  4. timeout_action(decisions, policy)             -> TimeoutAction
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum


@dataclass(frozen=True)
class Policy:
    task_type: str
    required: bool
    n_required: int
    m_total: int
    timeout_minutes: int | None
    auto_commit_on_timeout: bool

    def __post_init__(self):
        if self.n_required < 1:
            raise ValueError('n_required must be >= 1')
        if self.m_total < self.n_required:
            raise ValueError('m_total must be >= n_required')


@dataclass(frozen=True)
class Decision:
    decision: str  # APPROVE | REJECT | REQUEST_AMENDMENTS
    reviewed_by: str
    decided_at: datetime


@dataclass(frozen=True)
class QuorumResult:
    reached: bool                           # True when collected >= n_required
    collected: int                          # decisions present
    n_required: int
    m_total: int
    consensus: str | None                   # APPROVE / REJECT / REQUEST_AMENDMENTS / null


class TimeoutAction(str, Enum):
    WAIT = 'WAIT'                          # not timed out yet, keep waiting
    AUTO_COMMIT = 'AUTO_COMMIT'              # timed out, policy says commit anyway
    ESCALATE_FAILED = 'ESCALATE_FAILED'      # timed out, no auto-commit -> mark FAILED


def requires_human_oversight(policy: Policy) -> bool:
    """Whether the task should pause for human review (vs auto-finalise)."""
    return bool(policy.required)


def evaluate_quorum(decisions: list[Decision], policy: Policy) -> QuorumResult:
    """Has enough decisions been collected? What is the consensus?

    Consensus rules (deterministic, hackathon-defensible):
      - If any reviewer voted REJECT - consensus = REJECT (most-conservative wins).
      - Else if any voted REQUEST_AMENDMENTS - consensus = REQUEST_AMENDMENTS.
      - Else (all APPROVE)                 - consensus = APPROVE.
      - Below quorum                       - consensus = None.
    """
    collected = len(decisions)
    if collected < policy.n_required:
        return QuorumResult(reached=False, collected=collected, n_required=policy.n_required, m_total=policy.m_total, consensus=None)

    verdicts = {d.decision.upper() for d in decisions}
    if 'REJECT' in verdicts:
        consensus = 'REJECT'
    elif 'REQUEST_AMENDMENTS' in verdicts:
        consensus = 'REQUEST_AMENDMENTS'
    else:
        consensus = 'APPROVE'
    return QuorumResult(reached=True, collected=collected, n_required=policy.n_required, m_total=policy.m_total, consensus=consensus)


def is_timed_out(awaiting_since: datetime, policy: Policy, now: datetime | None = None) -> bool:
    if policy.timeout_minutes is None:
        return False
    now = now or datetime.now(timezone.utc)
    return (now - awaiting_since) >= timedelta(minutes=policy.timeout_minutes)


def timeout_action(decisions: list[Decision], policy: Policy, awaiting_since: datetime, now: datetime | None = None) -> TimeoutAction:
    if not is_timed_out(awaiting_since, policy, now):
        return TimeoutAction.WAIT
    return TimeoutAction.AUTO_COMMIT if policy.auto_commit_on_timeout else TimeoutAction.ESCALATE_FAILED
