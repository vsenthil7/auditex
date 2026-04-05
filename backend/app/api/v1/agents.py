"""
Auditex -- Agent routes.
POST /api/v1/agents              -- register a new agent
GET  /api/v1/agents              -- list agents
GET  /api/v1/agents/{agent_id}   -- get single agent
All routes require X-API-Key authentication.
"""
from __future__ import annotations

import json
import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.middleware.auth import require_api_key
from app.models.agent import AgentCreate, AgentResponse
from db.connection import get_db_session
from db.repositories import agent_repo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["agents"])


def _orm_to_response(agent) -> dict:
    capabilities = None
    if agent.capabilities:
        try:
            capabilities = json.loads(agent.capabilities)
        except Exception:
            capabilities = [agent.capabilities]
    return {
        "agent_id": str(agent.id),
        "name": agent.name,
        "agent_type": agent.agent_type,
        "model_version": agent.model_version,
        "is_active": agent.is_active,
        "capabilities": capabilities,
        "created_at": agent.created_at.isoformat(),
    }


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=dict,
    summary="Register a new agent",
)
async def create_agent(
    body: AgentCreate,
    _key_meta: dict = Depends(require_api_key),
    session=Depends(get_db_session),
):
    """Register a new AI agent or human actor in the agent registry."""
    agent = await agent_repo.create_agent(
        session,
        name=body.name,
        agent_type=body.agent_type,
        model_version=body.model_version,
        public_key=body.public_key,
        capabilities=body.capabilities,
        metadata=body.metadata,
    )
    logger.info("Agent created: %s name=%s type=%s", agent.id, agent.name, agent.agent_type)
    return _orm_to_response(agent)


@router.get(
    "",
    response_model=dict,
    summary="List registered agents",
)
async def list_agents(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    active_only: bool = Query(default=True, description="Return only active agents"),
    _key_meta: dict = Depends(require_api_key),
    session=Depends(get_db_session),
):
    """Paginated list of registered agents."""
    agents, total = await agent_repo.list_agents(
        session, page=page, page_size=page_size, active_only=active_only
    )
    return {
        "agents": [_orm_to_response(a) for a in agents],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get(
    "/{agent_id}",
    response_model=dict,
    summary="Get a single agent by ID",
)
async def get_agent(
    agent_id: uuid.UUID,
    _key_meta: dict = Depends(require_api_key),
    session=Depends(get_db_session),
):
    """Fetch a single agent by UUID."""
    agent = await agent_repo.get_agent(session, agent_id)
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found.",
        )
    return _orm_to_response(agent)
