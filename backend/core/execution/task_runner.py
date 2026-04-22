"""Auditex -- Task orchestration shim (Phase 11 Item 9).

Thin, reusable wrapper around the execute->review->consensus pipeline.
Kept deliberately small: it coordinates already-existing services and
provides a single async entrypoint for workers and any future HTTP sync
runner path. Does NOT own DB sessions -- caller manages the session.

Stages:
  1. execute  -> ClaudeExecutor.run_task()
  2. review   -> review.coordinator.run_review()
  3. consensus-> vertex_client.submit_hash_and_finalise()
Each stage returns a dict that is appended to the context history.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


class TaskRunnerError(Exception):
    """Raised when a stage fails in a way the caller must handle."""


@dataclass
class RunResult:
    """Accumulates per-stage output for one task run."""
    task_id: uuid.UUID
    executor_output: dict | None = None
    review_result: dict | None = None
    consensus_output: dict | None = None
    stages_completed: list[str] = field(default_factory=list)

    def mark_done(self, stage: str) -> None:
        self.stages_completed.append(stage)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": str(self.task_id),
            "executor_output": self.executor_output,
            "review_result": self.review_result,
            "consensus_output": self.consensus_output,
            "stages_completed": list(self.stages_completed),
        }


class TaskRunner:
    """Orchestrates execute -> review -> consensus for a single task."""

    def __init__(
        self,
        executor,
        reviewer,
        consensus,
        context: Any = None,
    ):
        """All collaborators injected so tests can pass mocks."""
        self._executor = executor
        self._reviewer = reviewer
        self._consensus = consensus
        self._context = context

    async def run(self, task_id: uuid.UUID, task_payload: dict) -> RunResult:
        """Run all three stages. Raises TaskRunnerError if any stage fails."""
        result = RunResult(task_id=task_id)

        # Stage 1 -- execute
        try:
            exec_out = await self._executor.run_task(task_id, task_payload)
        except Exception as exc:
            logger.error("execute stage failed task=%s err=%s", task_id, exc)
            raise TaskRunnerError(f"execute failed: {exc}") from exc
        result.executor_output = exec_out
        result.mark_done("execute")
        await self._record(task_id, "execute", "ok")

        # Stage 2 -- review
        try:
            review_out = await self._reviewer.run_review(task_id, exec_out)
        except Exception as exc:
            logger.error("review stage failed task=%s err=%s", task_id, exc)
            raise TaskRunnerError(f"review failed: {exc}") from exc
        result.review_result = review_out
        result.mark_done("review")
        await self._record(task_id, "review", "ok")

        # Stage 3 -- consensus
        try:
            cons_out = await self._consensus.submit_and_finalise(task_id, review_out)
        except Exception as exc:
            logger.error("consensus stage failed task=%s err=%s", task_id, exc)
            raise TaskRunnerError(f"consensus failed: {exc}") from exc
        result.consensus_output = cons_out
        result.mark_done("consensus")
        await self._record(task_id, "consensus", "ok")

        return result

    async def _record(self, task_id: uuid.UUID, step: str, note: str) -> None:
        """Append a history entry to the context, if one is attached."""
        if self._context is None:
            return
        try:
            await self._context.append_history(task_id, step, note=note)
        except Exception as exc:
            # History failures must not kill the task.
            logger.warning("history append failed task=%s err=%s", task_id, exc)
