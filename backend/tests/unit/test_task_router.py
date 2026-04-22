"""Tests for core.ingestion.task_router."""
from __future__ import annotations

import pytest

from core.ingestion.agent_registry import AgentRegistry
from core.ingestion.task_router import (
    NoEligibleAgentError, PayloadValidationError, TaskRouter,
)


@pytest.fixture
def registry():
    return AgentRegistry()


def test_route_happy_path_picks_first_eligible(registry):
    registry.register("agent-a", task_types=["audit"])
    router = TaskRouter(registry)
    result = router.route("audit", {"x": 1})
    assert result["agent_id"] == "agent-a"
    assert result["task_type"] == "audit"
    assert result["payload"] == {"x": 1}


def test_route_with_schema_valid(registry):
    schema = {"type": "object", "required": ["name"]}
    registry.register("a", task_types=["t"], payload_schema=schema)
    router = TaskRouter(registry)
    out = router.route("t", {"name": "x"})
    assert out["agent_id"] == "a"


def test_route_with_schema_invalid_raises(registry):
    schema = {"type": "object", "required": ["name"]}
    registry.register("a", task_types=["t"], payload_schema=schema)
    router = TaskRouter(registry)
    with pytest.raises(PayloadValidationError) as e:
        router.route("t", {})
    assert e.value.errors
    assert any("name" in err for err in e.value.errors)


def test_route_no_eligible_agent(registry):
    router = TaskRouter(registry)
    with pytest.raises(NoEligibleAgentError):
        router.route("anything", {})


def test_route_explicit_agent_id(registry):
    registry.register("a", task_types=["t"])
    registry.register("b", task_types=["t"])
    router = TaskRouter(registry)
    out = router.route("t", {}, agent_id="b")
    assert out["agent_id"] == "b"


def test_route_explicit_agent_id_unknown(registry):
    router = TaskRouter(registry)
    with pytest.raises(NoEligibleAgentError):
        router.route("t", {}, agent_id="ghost")


def test_route_explicit_agent_does_not_accept_type(registry):
    registry.register("a", task_types=["other"])
    router = TaskRouter(registry)
    with pytest.raises(NoEligibleAgentError):
        router.route("t", {}, agent_id="a")


def test_route_no_schema_means_no_validation(registry):
    registry.register("a", task_types=["t"])
    router = TaskRouter(registry)
    out = router.route("t", {"anything": "goes"})
    assert out["schema_errors"] == []
