"""Tests for core.execution.task_runner."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from core.execution.task_runner import (
    TaskRunner, TaskRunnerError, RunResult,
)


def _make_collaborators():
    executor = MagicMock()
    executor.run_task = AsyncMock(return_value={"stage": "exec"})
    reviewer = MagicMock()
    reviewer.run_review = AsyncMock(return_value={"consensus": "3_OF_3_APPROVE"})
    consensus = MagicMock()
    consensus.submit_and_finalise = AsyncMock(return_value={"event_hash": "h" * 64})
    return executor, reviewer, consensus


def test_run_result_to_dict_initially_empty():
    tid = uuid.uuid4()
    r = RunResult(task_id=tid)
    d = r.to_dict()
    assert d["task_id"] == str(tid)
    assert d["stages_completed"] == []
    assert d["executor_output"] is None


def test_run_result_mark_done_records_stage():
    r = RunResult(task_id=uuid.uuid4())
    r.mark_done("execute")
    r.mark_done("review")
    assert r.stages_completed == ["execute", "review"]


@pytest.mark.asyncio
async def test_run_happy_path_all_three_stages():
    executor, reviewer, consensus = _make_collaborators()
    runner = TaskRunner(executor, reviewer, consensus)
    tid = uuid.uuid4()
    result = await runner.run(tid, {"payload": 1})
    assert result.task_id == tid
    assert result.executor_output == {"stage": "exec"}
    assert result.review_result["consensus"] == "3_OF_3_APPROVE"
    assert result.consensus_output["event_hash"] == "h" * 64
    assert result.stages_completed == ["execute", "review", "consensus"]
    executor.run_task.assert_awaited_once()
    reviewer.run_review.assert_awaited_once()
    consensus.submit_and_finalise.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_stops_at_execute_failure():
    executor, reviewer, consensus = _make_collaborators()
    executor.run_task = AsyncMock(side_effect=RuntimeError("exec fail"))
    runner = TaskRunner(executor, reviewer, consensus)
    with pytest.raises(TaskRunnerError) as e:
        await runner.run(uuid.uuid4(), {})
    assert "execute failed" in str(e.value)
    reviewer.run_review.assert_not_awaited()
    consensus.submit_and_finalise.assert_not_awaited()


@pytest.mark.asyncio
async def test_run_stops_at_review_failure():
    executor, reviewer, consensus = _make_collaborators()
    reviewer.run_review = AsyncMock(side_effect=RuntimeError("rev fail"))
    runner = TaskRunner(executor, reviewer, consensus)
    with pytest.raises(TaskRunnerError) as e:
        await runner.run(uuid.uuid4(), {})
    assert "review failed" in str(e.value)
    consensus.submit_and_finalise.assert_not_awaited()


@pytest.mark.asyncio
async def test_run_stops_at_consensus_failure():
    executor, reviewer, consensus = _make_collaborators()
    consensus.submit_and_finalise = AsyncMock(side_effect=RuntimeError("cons fail"))
    runner = TaskRunner(executor, reviewer, consensus)
    with pytest.raises(TaskRunnerError) as e:
        await runner.run(uuid.uuid4(), {})
    assert "consensus failed" in str(e.value)


@pytest.mark.asyncio
async def test_run_with_context_records_each_stage():
    executor, reviewer, consensus = _make_collaborators()
    ctx = MagicMock()
    ctx.append_history = AsyncMock()
    runner = TaskRunner(executor, reviewer, consensus, context=ctx)
    await runner.run(uuid.uuid4(), {})
    assert ctx.append_history.await_count == 3
    steps = [c.args[1] for c in ctx.append_history.await_args_list]
    assert steps == ["execute", "review", "consensus"]


@pytest.mark.asyncio
async def test_run_history_failure_does_not_kill_task():
    executor, reviewer, consensus = _make_collaborators()
    ctx = MagicMock()
    ctx.append_history = AsyncMock(side_effect=RuntimeError("history down"))
    runner = TaskRunner(executor, reviewer, consensus, context=ctx)
    result = await runner.run(uuid.uuid4(), {})
    assert result.stages_completed == ["execute", "review", "consensus"]


@pytest.mark.asyncio
async def test_run_without_context_skips_history():
    executor, reviewer, consensus = _make_collaborators()
    runner = TaskRunner(executor, reviewer, consensus, context=None)
    # Should complete without any error even though ctx is None
    result = await runner.run(uuid.uuid4(), {})
    assert len(result.stages_completed) == 3
