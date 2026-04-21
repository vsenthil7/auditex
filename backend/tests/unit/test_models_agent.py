"""Tests for app.models.agent pydantic schemas (HTTP layer)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.models.agent import AgentCreate, AgentListResponse, AgentResponse


def test_agent_create_valid():
    a = AgentCreate(name="Claude executor", agent_type="claude")
    assert a.name == "Claude executor"
    assert a.model_version is None
    assert a.capabilities is None


def test_agent_create_full():
    a = AgentCreate(
        name="Claude executor",
        agent_type="claude",
        model_version="claude-sonnet-4-6",
        public_key="PEM",
        capabilities=["document_review", "risk_analysis"],
        metadata={"team": "finance"},
    )
    assert a.capabilities == ["document_review", "risk_analysis"]
    assert a.metadata == {"team": "finance"}


def test_agent_create_empty_name():
    with pytest.raises(ValidationError):
        AgentCreate(name="", agent_type="claude")


def test_agent_create_name_too_long():
    with pytest.raises(ValidationError):
        AgentCreate(name="x" * 300, agent_type="claude")


def test_agent_response_shape():
    r = AgentResponse(
        agent_id=uuid.uuid4(),
        name="x",
        agent_type="human",
        model_version=None,
        is_active=True,
        capabilities=None,
        created_at=datetime.now(timezone.utc),
    )
    assert r.is_active is True


def test_agent_list_response_shape():
    r = AgentResponse(
        agent_id=uuid.uuid4(),
        name="x",
        agent_type="human",
        model_version=None,
        is_active=True,
        capabilities=None,
        created_at=datetime.now(timezone.utc),
    )
    lst = AgentListResponse(agents=[r], total=1)
    assert lst.total == 1
