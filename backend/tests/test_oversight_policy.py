"""Unit tests for core/review/oversight_policy.py - HIL-5 policy logic.

Pure function tests, no DB / no Celery / no HTTP. Targets 100%% line coverage of the module."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from core.review.oversight_policy import (
    Decision,
    Policy,
    QuorumResult,
    TimeoutAction,
    evaluate_quorum,
    is_timed_out,
    requires_human_oversight,
    timeout_action,
)


# ---------------------------------------------------------------------------
# Policy validation
# ---------------------------------------------------------------------------

def test_policy_valid():
    p = Policy(task_type='x', required=True, n_required=2, m_total=3, timeout_minutes=60, auto_commit_on_timeout=True)
    assert p.n_required == 2 and p.m_total == 3


def test_policy_rejects_n_lt_1():
    with pytest.raises(ValueError):
        Policy(task_type='x', required=True, n_required=0, m_total=1, timeout_minutes=None, auto_commit_on_timeout=False)


def test_policy_rejects_m_lt_n():
    with pytest.raises(ValueError):
        Policy(task_type='x', required=True, n_required=3, m_total=2, timeout_minutes=None, auto_commit_on_timeout=False)


# ---------------------------------------------------------------------------
# requires_human_oversight
# ---------------------------------------------------------------------------

def test_requires_oversight_true():
    p = Policy('x', True, 1, 1, None, False)
    assert requires_human_oversight(p) is True


def test_requires_oversight_false():
    p = Policy('x', False, 1, 1, None, False)
    assert requires_human_oversight(p) is False


# ---------------------------------------------------------------------------
# evaluate_quorum
# ---------------------------------------------------------------------------

def _d(decision, reviewed_by='alice'):
    return Decision(decision=decision, reviewed_by=reviewed_by, decided_at=datetime.now(timezone.utc))


def test_quorum_below_threshold():
    p = Policy('x', True, 2, 3, None, False)
    r = evaluate_quorum([_d('APPROVE')], p)
    assert r.reached is False and r.consensus is None and r.collected == 1


def test_quorum_all_approve():
    p = Policy('x', True, 2, 3, None, False)
    r = evaluate_quorum([_d('APPROVE'), _d('APPROVE', 'bob')], p)
    assert r.reached is True and r.consensus == 'APPROVE'


def test_quorum_reject_overrides_approve():
    p = Policy('x', True, 2, 3, None, False)
    r = evaluate_quorum([_d('APPROVE'), _d('REJECT', 'bob')], p)
    assert r.reached is True and r.consensus == 'REJECT'


def test_quorum_request_amendments_when_no_reject():
    p = Policy('x', True, 2, 3, None, False)
    r = evaluate_quorum([_d('APPROVE'), _d('REQUEST_AMENDMENTS', 'bob')], p)
    assert r.reached is True and r.consensus == 'REQUEST_AMENDMENTS'


def test_quorum_lowercase_decisions():
    # tolerance: case-insensitive verdict tags
    p = Policy('x', True, 1, 1, None, False)
    r = evaluate_quorum([_d('approve')], p)
    assert r.consensus == 'APPROVE'


# ---------------------------------------------------------------------------
# is_timed_out + timeout_action
# ---------------------------------------------------------------------------

def test_no_timeout_when_minutes_none():
    p = Policy('x', True, 1, 1, None, False)
    long_ago = datetime.now(timezone.utc) - timedelta(days=365)
    assert is_timed_out(long_ago, p) is False


def test_timeout_not_yet():
    p = Policy('x', True, 1, 1, 60, False)
    recently = datetime.now(timezone.utc) - timedelta(minutes=5)
    assert is_timed_out(recently, p) is False


def test_timeout_yes():
    p = Policy('x', True, 1, 1, 60, False)
    long_ago = datetime.now(timezone.utc) - timedelta(hours=2)
    assert is_timed_out(long_ago, p) is True


def test_timeout_action_wait():
    p = Policy('x', True, 1, 1, 60, True)
    recently = datetime.now(timezone.utc) - timedelta(minutes=5)
    assert timeout_action([], p, recently) == TimeoutAction.WAIT


def test_timeout_action_auto_commit():
    p = Policy('x', True, 1, 1, 60, True)
    long_ago = datetime.now(timezone.utc) - timedelta(hours=2)
    assert timeout_action([], p, long_ago) == TimeoutAction.AUTO_COMMIT


def test_timeout_action_escalate_failed():
    p = Policy('x', True, 1, 1, 60, False)
    long_ago = datetime.now(timezone.utc) - timedelta(hours=2)
    assert timeout_action([], p, long_ago) == TimeoutAction.ESCALATE_FAILED
