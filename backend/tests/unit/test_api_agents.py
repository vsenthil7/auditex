"""Tests for app.api.v1.agents route handlers."""
from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.v1 import agents as agents_api
from app.models.agent import AgentCreate


def test_orm_to_response_full(sample_agent):
    sample_agent.created_at = MagicMock()
    sample_agent.created_at.isoformat = MagicMock(return_value="2026-04-21T00:00:00")
    out = agents_api._orm_to_response(sample_agent)
    assert out["name"] == "Test Agent"
    assert out["agent_type"] == "claude"
    assert out["capabilities"] == ["document_review"]


def test_orm_to_response_bad_capabilities_json():
    a = MagicMock()
    a.id = uuid.uuid4()
    a.name = "x"
    a.agent_type = "claude"
    a.model_version = None
    a.is_active = True
    a.capabilities = "not valid json"
    a.created_at = MagicMock()
    a.created_at.isoformat = MagicMock(return_value="2026-04-21T00:00:00")
    out = agents_api._orm_to_response(a)
    # Fallback to wrapping string in a list
    assert out["capabilities"] == ["not valid json"]


def test_orm_to_response_no_capabilities():
    a = MagicMock()
    a.id = uuid.uuid4()
    a.name = "x"
    a.agent_type = "claude"
    a.model_version = None
    a.is_active = True
    a.capabilities = None
    a.created_at = MagicMock()
    a.created_at.isoformat = MagicMock(return_value="2026-04-21T00:00:00")
    out = agents_api._orm_to_response(a)
    assert out["capabilities"] is None


@pytest.mark.asyncio
async def test_create_agent(mock_async_session, sample_agent):
    body = AgentCreate(
        name="Claude Exec", agent_type="claude",
        model_version="claude-sonnet-4-6",
        capabilities=["document_review"],
    )
    sample_agent.created_at.isoformat = MagicMock(return_value="2026-04-21T00:00:00")
    with patch.object(agents_api.agent_repo, "create_agent", AsyncMock(return_value=sample_agent)):
        out = await agents_api.create_agent(body, {}, mock_async_session)
    assert out["name"] == sample_agent.name


@pytest.mark.asyncio
async def test_list_agents(mock_async_session, sample_agent):
    sample_agent.created_at.isoformat = MagicMock(return_value="2026-04-21T00:00:00")
    with patch.object(
        agents_api.agent_repo, "list_agents",
        AsyncMock(return_value=([sample_agent], 1)),
    ):
        out = await agents_api.list_agents(
            page=1, page_size=20, active_only=True,
            _key_meta={}, session=mock_async_session,
        )
    assert out["total"] == 1


@pytest.mark.asyncio
async def test_get_agent_found(mock_async_session, sample_agent):
    sample_agent.created_at.isoformat = MagicMock(return_value="2026-04-21T00:00:00")
    with patch.object(agents_api.agent_repo, "get_agent", AsyncMock(return_value=sample_agent)):
        out = await agents_api.get_agent(sample_agent.id, {}, mock_async_session)
    assert out["agent_id"] == str(sample_agent.id)


@pytest.mark.asyncio
async def test_get_agent_not_found(mock_async_session):
    with patch.object(agents_api.agent_repo, "get_agent", AsyncMock(return_value=None)):
        with pytest.raises(HTTPException) as e:
            await agents_api.get_agent(uuid.uuid4(), {}, mock_async_session)
    assert e.value.status_code == 404
