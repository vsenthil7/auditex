"""Auditex -- In-memory agent capability registry (Phase 11 Item 10).

Tracks which agents are online, what task types they accept, and what
payload schema they expect. Used by TaskRouter at ingestion time to pick
a target agent and to validate the payload before enqueuing the task.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field


class AgentAlreadyRegisteredError(Exception):
    """Raised when registering an agent_id that already exists."""


class AgentNotFoundError(Exception):
    """Raised when get/unregister is called with an unknown agent_id."""


@dataclass
class AgentRegistration:
    agent_id: str
    task_types: list[str] = field(default_factory=list)
    payload_schema: dict = field(default_factory=dict)
    description: str = ""

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "task_types": list(self.task_types),
            "payload_schema": dict(self.payload_schema),
            "description": self.description,
        }


class AgentRegistry:
    """Thread-safe in-memory registry of agent capabilities."""

    def __init__(self):
        self._agents: dict[str, AgentRegistration] = {}
        self._lock = threading.Lock()

    def register(
        self, agent_id: str, *, task_types: list[str],
        payload_schema: dict | None = None, description: str = "",
    ) -> AgentRegistration:
        with self._lock:
            if agent_id in self._agents:
                raise AgentAlreadyRegisteredError(f"Agent {agent_id} already registered.")
            reg = AgentRegistration(
                agent_id=agent_id, task_types=list(task_types),
                payload_schema=dict(payload_schema or {}), description=description,
            )
            self._agents[agent_id] = reg
            return reg

    def unregister(self, agent_id: str) -> None:
        with self._lock:
            if agent_id not in self._agents:
                raise AgentNotFoundError(f"Agent {agent_id} not found.")
            del self._agents[agent_id]

    def get(self, agent_id: str) -> AgentRegistration:
        with self._lock:
            if agent_id not in self._agents:
                raise AgentNotFoundError(f"Agent {agent_id} not found.")
            return self._agents[agent_id]

    def list_agents(self) -> list[AgentRegistration]:
        with self._lock:
            return list(self._agents.values())

    def find_by_task_type(self, task_type: str) -> list[AgentRegistration]:
        with self._lock:
            return [a for a in self._agents.values() if task_type in a.task_types]

    def clear(self) -> None:
        """Drop all registrations -- for tests and process restart."""
        with self._lock:
            self._agents.clear()


_default_registry: AgentRegistry | None = None


def get_default_registry() -> AgentRegistry:
    global _default_registry
    if _default_registry is None:
        _default_registry = AgentRegistry()
    return _default_registry


def reset_default_registry() -> None:
    global _default_registry
    _default_registry = None
