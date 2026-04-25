"""
Auditex - Article 14 Human Oversight routes.
GET  /api/v1/human-review/queue                       - tasks awaiting human review
POST /api/v1/tasks/{task_id}/human-decision           - record a decision
GET  /api/v1/human-oversight-policies                 - list policies (admin)
PUT  /api/v1/human-oversight-policies/{task_type}     - upsert policy (admin)
All routes require X-API-Key authentication.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.api.middleware.auth import require_api_key
from app.models.human_review import (
    HumanDecisionRequest,
    HumanDecisionResponse,
    HumanOversightPolicySchema,
    HumanReviewQueueResponse,
    HumanOversightPolicyListResponse,
)
from db.connection import get_db_session
from db.repositories import human_oversight_repo, task_repo, event_repo
from db.models.task import Task
from core.review.oversight_policy import (
    Policy as OversightPolicy,
    Decision as OversightDecision,
    evaluate_quorum,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["human-review"])

def _task_to_queue_dict(task: Task) -> dict:
    return {
        "task_id": str(task.id),
        "task_type": task.task_type,
        "status": task.status,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "consensus_result": task.consensus_result,
        "workflow_id": task.workflow_id,
        "report_available": bool(task.report_available),
    }

@router.get("/human-review/queue", response_model=HumanReviewQueueResponse, dependencies=[Depends(require_api_key)])
async def list_human_review_queue(session=Depends(get_db_session)):
    res = await session.execute(select(Task).where(Task.status == "AWAITING_HUMAN_REVIEW").order_by(Task.created_at))
    rows = list(res.scalars().all())
    return HumanReviewQueueResponse(tasks=[_task_to_queue_dict(t) for t in rows], total=len(rows))

@router.post("/tasks/{task_id}/human-decision", response_model=HumanDecisionResponse, dependencies=[Depends(require_api_key)])
async def record_human_decision(task_id: uuid.UUID, body: HumanDecisionRequest, session=Depends(get_db_session)):
    task = await task_repo.get_task(session, task_id=task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    if task.status != "AWAITING_HUMAN_REVIEW":
        raise HTTPException(status_code=409, detail=f"task is in status {task.status}, not AWAITING_HUMAN_REVIEW")
    if await human_oversight_repo.has_reviewed(session, task_id=task_id, reviewed_by=body.reviewed_by):
        raise HTTPException(status_code=409, detail=f"reviewer {body.reviewed_by} already decided on this task")
    decided_at = datetime.now(timezone.utc)
    decision_row = await human_oversight_repo.insert_decision(session, task_id=task_id, decision=body.decision.value, reason=body.reason, reviewed_by=body.reviewed_by, decided_at=decided_at)
    await event_repo.insert_event(session, task_id=task_id, event_type="human_decision_recorded", payload={"decision": body.decision.value, "reviewed_by": body.reviewed_by, "reason": body.reason[:500], "decided_at": decided_at.isoformat()})
    # Check quorum
    policy_row = await human_oversight_repo.get_policy(session, task_type=task.task_type)
    if policy_row is None:
        await session.commit()
        return HumanDecisionResponse(task_id=task_id, decision=body.decision, reviewed_by=body.reviewed_by, decided_at=decided_at, quorum_reached=False, n_collected=1, n_required=1, m_total=1, consensus=None, task_status=task.status)
    policy = OversightPolicy(task_type=policy_row.task_type, required=bool(policy_row.required), n_required=int(policy_row.n_required), m_total=int(policy_row.m_total), timeout_minutes=policy_row.timeout_minutes, auto_commit_on_timeout=bool(policy_row.auto_commit_on_timeout))
    decisions = await human_oversight_repo.list_decisions_for_task(session, task_id=task_id)
    quorum_input = [OversightDecision(decision=d.decision, reviewed_by=d.reviewed_by, decided_at=d.decided_at) for d in decisions]
    quorum = evaluate_quorum(quorum_input, policy)
    new_status = task.status
    if quorum.reached:
        # HIL-8: flip to FINALISING + dispatch Celery task to do Vertex submit + COMPLETED
        new_status = "FINALISING"
        await task_repo.update_task_status(session, task_id=task_id, status=new_status)
        await event_repo.insert_event(session, task_id=task_id, event_type="human_quorum_reached", payload={"consensus": quorum.consensus, "collected": quorum.collected, "n_required": quorum.n_required, "m_total": quorum.m_total})
        try:
            from workers.execution_worker import finalise_after_human_review
            finalise_after_human_review.delay(str(task_id))
            logger.info("human-decision: dispatched finalise_after_human_review | task=%s", task_id)
        except Exception as exc:
            logger.error("human-decision: failed to dispatch finalisation | task=%s: %s", task_id, exc)
    await session.commit()
    return HumanDecisionResponse(task_id=task_id, decision=body.decision, reviewed_by=body.reviewed_by, decided_at=decided_at, quorum_reached=quorum.reached, n_collected=quorum.collected, n_required=quorum.n_required, m_total=quorum.m_total, consensus=quorum.consensus, task_status=new_status)

@router.get("/human-oversight-policies", response_model=HumanOversightPolicyListResponse, dependencies=[Depends(require_api_key)])
async def list_human_oversight_policies(session=Depends(get_db_session)):
    rows = await human_oversight_repo.list_policies(session)
    items = [HumanOversightPolicySchema(task_type=r.task_type, required=bool(r.required), n_required=int(r.n_required), m_total=int(r.m_total), timeout_minutes=r.timeout_minutes, auto_commit_on_timeout=bool(r.auto_commit_on_timeout)) for r in rows]
    return HumanOversightPolicyListResponse(policies=items)

@router.put("/human-oversight-policies/{task_type}", response_model=HumanOversightPolicySchema, dependencies=[Depends(require_api_key)])
async def update_human_oversight_policy(task_type: str, body: HumanOversightPolicySchema, session=Depends(get_db_session)):
    if body.task_type != task_type:
        raise HTTPException(status_code=400, detail="task_type in URL must match body")
    if body.m_total < body.n_required:
        raise HTTPException(status_code=400, detail="m_total must be >= n_required")
    if body.n_required < 1:
        raise HTTPException(status_code=400, detail="n_required must be >= 1")
    row = await human_oversight_repo.upsert_policy(session, task_type=task_type, required=body.required, n_required=body.n_required, m_total=body.m_total, timeout_minutes=body.timeout_minutes, auto_commit_on_timeout=body.auto_commit_on_timeout)
    await session.commit()
    return HumanOversightPolicySchema(task_type=row.task_type, required=bool(row.required), n_required=int(row.n_required), m_total=int(row.m_total), timeout_minutes=row.timeout_minutes, auto_commit_on_timeout=bool(row.auto_commit_on_timeout))
