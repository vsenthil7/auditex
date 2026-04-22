"""Tests for core.ingestion.agent_registry."""
from __future__ import annotations

import pytest

from core.ingestion.agent_registry import (
    AgentAlreadyRegisteredError, AgentNotFoundError,
    AgentRegistration, AgentRegistry,
    get_default_registry, reset_default_registry,
)


@pytest.fixture(autouse=True)
def _reset_singleton():
    reset_default_registry()
    yield
    reset_default_registry()


def test_register_and_get():
    r = AgentRegistry()
    r.register("a1", task_types=["t"], payload_schema={"type": "object"}, description="d")
    got = r.get("a1")
    assert got.agent_id == "a1"
    assert got.task_types == ["t"]
    assert got.description == "d"


def test_register_duplicate_raises():
    r = AgentRegistry()
    r.register("a", task_types=[])
    with pytest.raises(AgentAlreadyRegisteredError):
        r.register("a", task_types=[])


def test_get_missing_raises():
    r = AgentRegistry()
    with pytest.raises(AgentNotFoundError):
        r.get("nope")


def test_unregister_removes():
    r = AgentRegistry()
    r.register("a", task_types=[])
    r.unregister("a")
    with pytest.raises(AgentNotFoundError):
        r.get("a")


def test_unregister_missing_raises():
    r = AgentRegistry()
    with pytest.raises(AgentNotFoundError):
        r.unregister("x")


def test_list_agents():
    r = AgentRegistry()
    r.register("a", task_types=[])
    r.register("b", task_types=[])
    ids = {a.agent_id for a in r.list_agents()}
    assert ids == {"a", "b"}


def test_find_by_task_type():
    r = AgentRegistry()
    r.register("a", task_types=["t1"])
    r.register("b", task_types=["t2"])
    r.register("c", task_types=["t1", "t2"])
    found = r.find_by_task_type("t1")
    ids = {a.agent_id for a in found}
    assert ids == {"a", "c"}


def test_find_by_task_type_none_match():
    r = AgentRegistry()
    r.register("a", task_types=["t1"])
    assert r.find_by_task_type("other") == []


def test_clear():
    r = AgentRegistry()
    r.register("a", task_types=[])
    r.clear()
    assert r.list_agents() == []


def test_registration_to_dict():
    reg = AgentRegistration(agent_id="x", task_types=["t"], payload_schema={"k": 1}, description="d")
    d = reg.to_dict()
    assert d["agent_id"] == "x"
    assert d["payload_schema"] == {"k": 1}


def test_default_registry_singleton():
    s1 = get_default_registry()
    s2 = get_default_registry()
    assert s1 is s2


def test_reset_default_registry_clears():
    s1 = get_default_registry()
    reset_default_registry()
    s2 = get_default_registry()
    assert s1 is not s2
