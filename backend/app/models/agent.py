"""
Auditex -- Pydantic schemas for Agent API.
These are the request/response models for the HTTP layer.
NOT the ORM models (those live in db/models/agent.py).
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AgentCreate(BaseModel):
    """Request body for POST /api/v1/agents."""
    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Human-readable agent name.",
        examples=["System Agent -- Claude Executor"],
    )
    agent_type: str = Field(
        ...,
        description="Agent category: claude | gpt4o | human | system",
        examples=["claude"],
    )
    model_version: str | None = Field(
        default=None,
        max_length=100,
        description="Exact model version string.",
        examples=["claude-sonnet-4-6"],
    )
    public_key: str | None = Field(
        default=None,
        description="PEM-encoded public key for cryptographic identity.",
    )
    capabilities: list[str] | None = Field(
        default=None,
        description="List of task types this agent can execute.",
        examples=[["document_review", "risk_analysis"]],
    )
    metadata: dict[str, Any] | None = Field(
        default=None,
        description="Arbitrary metadata key-value pairs.",
    )


class AgentResponse(BaseModel):
    """Response body for agent endpoints."""
    agent_id: uuid.UUID = Field(..., description="Unique agent identifier.")
    name: str
    agent_type: str
    model_version: str | None
    is_active: bool
    capabilities: list[str] | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AgentListResponse(BaseModel):
    """Paginated list of agents."""
    agents: list[AgentResponse]
    total: int
