"""Auditex -- Task router (Phase 11 Item 10).

Entry point for incoming tasks. For a given (task_type, payload) pair:
  1. Picks a registered agent that accepts task_type.
  2. Validates the payload against that agent payload_schema.
  3. Returns a routing decision dict the caller can enqueue.
"""
from __future__ import annotations

from core.ingestion.agent_registry import (
    AgentNotFoundError, AgentRegistry, AgentRegistration,
)
from core.ingestion.schema_validator import validate_payload


class NoEligibleAgentError(Exception):
    """No registered agent accepts the given task_type."""


class PayloadValidationError(Exception):
    """Payload failed schema validation against the chosen agent."""
    def __init__(self, message: str, errors: list[str]):
        super().__init__(message)
        self.errors = errors


class TaskRouter:
    def __init__(self, registry: AgentRegistry):
        self._registry = registry

    def route(self, task_type: str, payload: dict, *, agent_id: str | None = None) -> dict:
        """Decide which agent handles this task and validate payload.

        If agent_id is given, use that agent directly (and verify it accepts the
        task_type). Otherwise pick the first registered agent that lists this
        task_type in its capabilities.

        Returns a dict: {agent_id, task_type, payload, schema_errors: []}.
        Raises NoEligibleAgentError or PayloadValidationError on failure.
        """
        agent = self._select_agent(task_type, agent_id)
        if agent.payload_schema:
            ok, errors = validate_payload(agent.payload_schema, payload)
            if not ok:
                raise PayloadValidationError(
                    f"Payload invalid for agent {agent.agent_id}.",
                    errors=errors,
                )
        return {
            "agent_id": agent.agent_id,
            "task_type": task_type,
            "payload": payload,
            "schema_errors": [],
        }

    def _select_agent(self, task_type: str, agent_id: str | None) -> AgentRegistration:
        if agent_id is not None:
            try:
                agent = self._registry.get(agent_id)
            except AgentNotFoundError as exc:
                raise NoEligibleAgentError(str(exc)) from exc
            if task_type not in agent.task_types:
                raise NoEligibleAgentError(
                    f"Agent {agent_id} does not accept task_type={task_type}.",
                )
            return agent
        candidates = self._registry.find_by_task_type(task_type)
        if not candidates:
            raise NoEligibleAgentError(f"No agent accepts task_type={task_type}.")
        return candidates[0]
