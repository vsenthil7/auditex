"""
Auditex -- Agent repository.
All database access for the agents table goes through here.
"""
from __future__ import annotations

import json
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.agent import Agent


async def create_agent(
    session: AsyncSession,
    *,
    name: str,
    agent_type: str,
    model_version: str | None = None,
    public_key: str | None = None,
    capabilities: list[str] | None = None,
    metadata: dict | None = None,
) -> Agent:
    """Insert a new Agent record. Returns the persisted Agent."""
    agent = Agent(
        name=name,
        agent_type=agent_type,
        model_version=model_version,
        public_key=public_key,
        capabilities=json.dumps(capabilities) if capabilities is not None else None,
        metadata_json=json.dumps(metadata) if metadata is not None else None,
        is_active=True,
    )
    session.add(agent)
    await session.flush()
    await session.refresh(agent)
    return agent


async def get_agent(
    session: AsyncSession,
    agent_id: uuid.UUID,
) -> Agent | None:
    """Fetch a single Agent by UUID. Returns None if not found."""
    result = await session.execute(select(Agent).where(Agent.id == agent_id))
    return result.scalar_one_or_none()


async def get_agent_by_name(
    session: AsyncSession,
    name: str,
) -> Agent | None:
    """Fetch an Agent by name. Returns None if not found."""
    result = await session.execute(select(Agent).where(Agent.name == name))
    return result.scalar_one_or_none()


async def list_agents(
    session: AsyncSession,
    *,
    page: int = 1,
    page_size: int = 20,
    active_only: bool = True,
) -> tuple[list[Agent], int]:
    """
    Paginated agent list. Returns (agents, total_count).
    By default returns only active agents.
    """
    query = select(Agent)
    count_query = select(func.count()).select_from(Agent)

    if active_only:
        query = query.where(Agent.is_active == True)  # noqa: E712
        count_query = count_query.where(Agent.is_active == True)  # noqa: E712

    query = query.order_by(Agent.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await session.execute(query)
    agents = list(result.scalars().all())

    count_result = await session.execute(count_query)
    total = count_result.scalar_one()

    return agents, total
