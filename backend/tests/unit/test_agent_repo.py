"""Tests for db.repositories.agent_repo."""
from __future__ import annotations

import json
import uuid

import pytest

from db.repositories import agent_repo


@pytest.mark.asyncio
async def test_create_agent_full(mock_async_session):
    agent = await agent_repo.create_agent(
        mock_async_session,
        name="Claude",
        agent_type="claude",
        model_version="claude-sonnet-4-6",
        public_key="PEM",
        capabilities=["document_review"],
        metadata={"x": 1},
    )
    assert agent.name == "Claude"
    assert agent.is_active is True
    assert json.loads(agent.capabilities) == ["document_review"]
    assert json.loads(agent.metadata_json) == {"x": 1}


@pytest.mark.asyncio
async def test_create_agent_minimal(mock_async_session):
    agent = await agent_repo.create_agent(
        mock_async_session, name="Human reviewer", agent_type="human",
    )
    assert agent.capabilities is None
    assert agent.metadata_json is None


@pytest.mark.asyncio
async def test_get_agent_found(mock_async_session, sample_agent):
    mock_async_session._result.scalar_one_or_none.return_value = sample_agent
    r = await agent_repo.get_agent(mock_async_session, sample_agent.id)
    assert r is sample_agent


@pytest.mark.asyncio
async def test_get_agent_not_found(mock_async_session):
    mock_async_session._result.scalar_one_or_none.return_value = None
    r = await agent_repo.get_agent(mock_async_session, uuid.uuid4())
    assert r is None


@pytest.mark.asyncio
async def test_get_agent_by_name_found(mock_async_session, sample_agent):
    mock_async_session._result.scalar_one_or_none.return_value = sample_agent
    r = await agent_repo.get_agent_by_name(mock_async_session, "Test Agent")
    assert r is sample_agent


@pytest.mark.asyncio
async def test_get_agent_by_name_not_found(mock_async_session):
    mock_async_session._result.scalar_one_or_none.return_value = None
    r = await agent_repo.get_agent_by_name(mock_async_session, "nobody")
    assert r is None


@pytest.mark.asyncio
async def test_list_agents_active_only(mock_async_session, sample_agent):
    mock_async_session._scalars.all.return_value = [sample_agent]
    mock_async_session._result.scalar_one.return_value = 1
    agents, total = await agent_repo.list_agents(mock_async_session, active_only=True)
    assert total == 1


@pytest.mark.asyncio
async def test_list_agents_include_inactive(mock_async_session, sample_agent):
    mock_async_session._scalars.all.return_value = [sample_agent]
    mock_async_session._result.scalar_one.return_value = 1
    agents, total = await agent_repo.list_agents(
        mock_async_session, page=1, page_size=20, active_only=False,
    )
    assert total == 1
