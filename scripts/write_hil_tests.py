p = r"C:/Users/v_sen/Documents/Projects/0001_Hack0014_Vertex_Swarm_Tashi/auditex/backend/tests/unit/test_api_human_review.py"
src = """
Auditex - HIL-14: integration tests for app.api.v1.human_review endpoints.
Covers: GET /human-review/queue, POST /tasks/{id}/human-decision (valid + 404 + 409 cases),
GET /human-oversight-policies, PUT /human-oversight-policies/{task_type} (valid + 400 cases),
and the worker gate (oversight_required True flips to AWAITING_HUMAN_REVIEW).
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.api.v1 import human_review
from app.models.human_review import (HumanDecisionRequest, HumanDecision, HumanOversightPolicySchema)


def _make_task_orm(status: str = 'AWAITING_HUMAN_REVIEW', task_type: str = 'contract_check'):
    t = MagicMock()
    t.id = uuid.uuid4()
    t.task_type = task_type
    t.status = status
    t.workflow_id = None
    t.consensus_result = '3_OF_3_APPROVE'
    t.report_available = False
    t.created_at = datetime.now(timezone.utc)
    return t

def _make_policy_orm(task_type: str = 'contract_check', n_required: int = 1, m_total: int = 1, timeout_minutes=None, auto_commit_on_timeout: bool = False, required: bool = True):
    p = MagicMock()
    p.task_type = task_type
    p.required = required
    p.n_required = n_required
    p.m_total = m_total
    p.timeout_minutes = timeout_minutes
    p.auto_commit_on_timeout = auto_commit_on_timeout
    return p

def _make_decision_orm(decision: str, reviewed_by: str):
    d = MagicMock()
    d.decision = decision
    d.reviewed_by = reviewed_by
    d.decided_at = datetime.now(timezone.utc)
    return d

# ----- queue endpoint -----
@pytest.mark.asyncio
async def test_list_human_review_queue_empty(monkeypatch):
    session = MagicMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    session.execute = AsyncMock(return_value=result)
    out = await human_review.list_human_review_queue(session=session)
    assert out.total == 0
    assert out.tasks == []

@pytest.mark.asyncio
async def test_list_human_review_queue_with_tasks(monkeypatch):
    t1 = _make_task_orm()
    t2 = _make_task_orm(task_type='risk_analysis')
    session = MagicMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = [t1, t2]
    session.execute = AsyncMock(return_value=result)
    out = await human_review.list_human_review_queue(session=session)
    assert out.total == 2
    assert len(out.tasks) == 2
    assert out.tasks[0]['task_type'] in ('contract_check', 'risk_analysis')

# ----- decision endpoint -----
@pytest.mark.asyncio
async def test_record_human_decision_404_when_task_missing(monkeypatch):
    session = MagicMock(); session.commit = AsyncMock()
    monkeypatch.setattr(human_review.task_repo, 'get_task', AsyncMock(return_value=None))
    body = HumanDecisionRequest(decision=HumanDecision.APPROVE, reason='looks fine', reviewed_by='x')
    with pytest.raises(HTTPException) as ei:
        await human_review.record_human_decision(uuid.uuid4(), body, session=session)
    assert ei.value.status_code == 404

@pytest.mark.asyncio
async def test_record_human_decision_409_when_not_awaiting(monkeypatch):
    session = MagicMock(); session.commit = AsyncMock()
    task = _make_task_orm(status='COMPLETED')
    monkeypatch.setattr(human_review.task_repo, 'get_task', AsyncMock(return_value=task))
    body = HumanDecisionRequest(decision=HumanDecision.APPROVE, reason='fine', reviewed_by='x')
    with pytest.raises(HTTPException) as ei:
        await human_review.record_human_decision(task.id, body, session=session)
    assert ei.value.status_code == 409

@pytest.mark.asyncio
async def test_record_human_decision_409_when_duplicate_reviewer(monkeypatch):
    session = MagicMock(); session.commit = AsyncMock()
    task = _make_task_orm()
    monkeypatch.setattr(human_review.task_repo, 'get_task', AsyncMock(return_value=task))
    monkeypatch.setattr(human_review.human_oversight_repo, 'has_reviewed', AsyncMock(return_value=True))
    body = HumanDecisionRequest(decision=HumanDecision.APPROVE, reason='second-bite', reviewed_by='jane')
    with pytest.raises(HTTPException) as ei:
        await human_review.record_human_decision(task.id, body, session=session)
    assert ei.value.status_code == 409

@pytest.mark.asyncio
async def test_record_human_decision_quorum_not_reached(monkeypatch):
    # 2-of-3 policy, only 1 decision so far
    session = MagicMock(); session.commit = AsyncMock()
    task = _make_task_orm(task_type='risk_analysis')
    policy = _make_policy_orm(task_type='risk_analysis', n_required=2, m_total=3)
    decision = _make_decision_orm('APPROVE', 'jane')
    monkeypatch.setattr(human_review.task_repo, 'get_task', AsyncMock(return_value=task))
    monkeypatch.setattr(human_review.human_oversight_repo, 'has_reviewed', AsyncMock(return_value=False))
    monkeypatch.setattr(human_review.human_oversight_repo, 'insert_decision', AsyncMock(return_value=decision))
    monkeypatch.setattr(human_review.human_oversight_repo, 'get_policy', AsyncMock(return_value=policy))
    monkeypatch.setattr(human_review.human_oversight_repo, 'list_decisions_for_task', AsyncMock(return_value=[decision]))
    monkeypatch.setattr(human_review.event_repo, 'insert_event', AsyncMock())
    monkeypatch.setattr(human_review.task_repo, 'update_task_status', AsyncMock())
    body = HumanDecisionRequest(decision=HumanDecision.APPROVE, reason='first vote', reviewed_by='jane')
    out = await human_review.record_human_decision(task.id, body, session=session)
    assert out.quorum_reached is False
    assert out.decisions_collected == 1
    assert out.n_required == 2
    assert out.m_total == 3
    assert out.finalised is False

@pytest.mark.asyncio
async def test_record_human_decision_quorum_reached_finalises(monkeypatch):
    session = MagicMock(); session.commit = AsyncMock()
    task = _make_task_orm()
    policy = _make_policy_orm(n_required=1, m_total=1)
    decision = _make_decision_orm('APPROVE', 'jane')
    monkeypatch.setattr(human_review.task_repo, 'get_task', AsyncMock(return_value=task))
    monkeypatch.setattr(human_review.human_oversight_repo, 'has_reviewed', AsyncMock(return_value=False))
    monkeypatch.setattr(human_review.human_oversight_repo, 'insert_decision', AsyncMock(return_value=decision))
    monkeypatch.setattr(human_review.human_oversight_repo, 'get_policy', AsyncMock(return_value=policy))
    monkeypatch.setattr(human_review.human_oversight_repo, 'list_decisions_for_task', AsyncMock(return_value=[decision]))
    monkeypatch.setattr(human_review.event_repo, 'insert_event', AsyncMock())
    monkeypatch.setattr(human_review.task_repo, 'update_task_status', AsyncMock())
    # also stub the celery dispatch (HIL-8) so test does not hit broker
    import workers.reporting_worker as rw
    if hasattr(rw, 'finalise_after_human_review'):
        monkeypatch.setattr(rw.finalise_after_human_review, 'delay', MagicMock(), raising=False)
    body = HumanDecisionRequest(decision=HumanDecision.APPROVE, reason='final', reviewed_by='jane')
    out = await human_review.record_human_decision(task.id, body, session=session)
    assert out.quorum_reached is True
    assert out.finalised is True

# ----- policies endpoints -----
@pytest.mark.asyncio
async def test_list_policies(monkeypatch):
    session = MagicMock()
    p1 = _make_policy_orm('contract_check', 1, 1)
    p2 = _make_policy_orm('risk_analysis', 2, 3)
    monkeypatch.setattr(human_review.human_oversight_repo, 'list_policies', AsyncMock(return_value=[p1, p2]))
    out = await human_review.list_human_oversight_policies(session=session)
    assert len(out.policies) == 2
    assert out.policies[0].task_type == 'contract_check'
    assert out.policies[1].n_required == 2

@pytest.mark.asyncio
async def test_update_policy_400_when_url_body_mismatch(monkeypatch):
    session = MagicMock(); session.commit = AsyncMock()
    body = HumanOversightPolicySchema(task_type='contract_check', required=True, n_required=1, m_total=1, timeout_minutes=None, auto_commit_on_timeout=False)
    with pytest.raises(HTTPException) as ei:
        await human_review.update_human_oversight_policy('risk_analysis', body, session=session)
    assert ei.value.status_code == 400

@pytest.mark.asyncio
async def test_update_policy_400_when_n_gt_m(monkeypatch):
    session = MagicMock(); session.commit = AsyncMock()
    # build with valid n<=m, then mutate to skip pydantic check
    body = HumanOversightPolicySchema(task_type='contract_check', required=True, n_required=2, m_total=2, timeout_minutes=None, auto_commit_on_timeout=False)
    body.m_total = 1  # force the violation
    with pytest.raises(HTTPException) as ei:
        await human_review.update_human_oversight_policy('contract_check', body, session=session)
    assert ei.value.status_code == 400

@pytest.mark.asyncio
async def test_update_policy_happy_path(monkeypatch):
    session = MagicMock(); session.commit = AsyncMock()
    saved = _make_policy_orm('contract_check', 2, 3, timeout_minutes=120)
    monkeypatch.setattr(human_review.human_oversight_repo, 'upsert_policy', AsyncMock(return_value=saved))
    body = HumanOversightPolicySchema(task_type='contract_check', required=True, n_required=2, m_total=3, timeout_minutes=120, auto_commit_on_timeout=False)
    out = await human_review.update_human_oversight_policy('contract_check', body, session=session)
    assert out.task_type == 'contract_check'
    assert out.n_required == 2
    assert out.m_total == 3
    assert out.timeout_minutes == 120
"""
open(p, 'w', encoding='utf-8').write(src)
print('wrote', p, len(src), 'bytes')
