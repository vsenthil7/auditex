"""
Auditex - Pydantic schemas for Article 14 Human Oversight (HIL).

Endpoints (HIL-7):
  GET    /api/v1/human-review/queue
  POST   /api/v1/tasks/{id}/human-decision
  GET    /api/v1/human-oversight-policies
  PUT    /api/v1/human-oversight-policies/{task_type}
"""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class HumanDecision(str, Enum):
    APPROVE = 'APPROVE'
    REJECT = 'REJECT'
    REQUEST_AMENDMENTS = 'REQUEST_AMENDMENTS'


class HumanDecisionRequest(BaseModel):
    decision: HumanDecision = Field(..., description='APPROVE | REJECT | REQUEST_AMENDMENTS')
    reason: str = Field(..., min_length=1, max_length=2000, description='Reviewer reasoning (Article 14 traceability).')
    reviewed_by: str = Field(..., min_length=1, max_length=255, description='Natural-person reviewer identifier.')


class HumanDecisionResponse(BaseModel):
    task_id: uuid.UUID
    decision: HumanDecision
    reviewed_by: str
    decided_at: datetime
    decisions_collected: int = Field(..., description='Number of human decisions on this task.')
    n_required: int = Field(..., description='N from N-of-M policy.')
    m_total: int = Field(..., description='M from N-of-M policy.')
    quorum_reached: bool = Field(..., description='True when decisions_collected >= n_required.')
    finalised: bool = Field(..., description='True if quorum reached and Vertex commit triggered.')


class HumanOversightPolicySchema(BaseModel):
    task_type: str
    required: bool = Field(..., description='If False, this task type bypasses human review entirely.')
    n_required: int = Field(..., ge=1, description='Decisions needed to reach quorum.')
    m_total: int = Field(..., ge=1, description='Total reviewer slots; n_required <= m_total.')
    timeout_minutes: int | None = Field(default=None, description='Auto-action after this many minutes; None = wait forever.')
    auto_commit_on_timeout: bool = Field(default=False, description='On timeout, commit anyway (true) or escalate to FAILED (false).')

    model_config = {'from_attributes': True}


class HumanOversightPolicyListResponse(BaseModel):
    policies: list[HumanOversightPolicySchema]


class HumanReviewQueueResponse(BaseModel):
    tasks: list[dict]  # uses TaskResponse-shaped dicts; loose typed for forward-compat
    total: int
