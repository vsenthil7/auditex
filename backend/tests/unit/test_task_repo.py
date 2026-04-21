"""Tests for db.repositories.task_repo."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from db.repositories import task_repo


@pytest.mark.asyncio
async def test_create_task(mock_async_session):
    task = await task_repo.create_task(
        mock_async_session,
        task_type="document_review",
        payload={"foo": "bar"},
        submitted_by="alice",
        workflow_id="wf1",
        api_key_id="key1",
    )
    assert task.task_type == "document_review"
    assert task.status == "QUEUED"
    assert json.loads(task.payload_json) == {"foo": "bar"}
    assert task.submitted_by == "alice"
    mock_async_session.add.assert_called_once()
    mock_async_session.flush.assert_awaited()
    mock_async_session.refresh.assert_awaited()


@pytest.mark.asyncio
async def test_get_task_found(mock_async_session, sample_task):
    mock_async_session._result.scalar_one_or_none.return_value = sample_task
    result = await task_repo.get_task(mock_async_session, sample_task.id)
    assert result is sample_task


@pytest.mark.asyncio
async def test_get_task_not_found(mock_async_session):
    mock_async_session._result.scalar_one_or_none.return_value = None
    result = await task_repo.get_task(mock_async_session, uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_list_tasks_no_filter(mock_async_session, sample_task):
    mock_async_session._scalars.all.return_value = [sample_task]
    mock_async_session._result.scalar_one.return_value = 1
    tasks, total = await task_repo.list_tasks(mock_async_session)
    assert len(tasks) == 1
    assert total == 1


@pytest.mark.asyncio
async def test_list_tasks_with_status_filter(mock_async_session, sample_task):
    mock_async_session._scalars.all.return_value = [sample_task]
    mock_async_session._result.scalar_one.return_value = 1
    tasks, total = await task_repo.list_tasks(
        mock_async_session, page=2, page_size=5, status_filter="COMPLETED",
    )
    assert total == 1


@pytest.mark.asyncio
async def test_update_task_status_full_fields(mock_async_session, sample_task):
    mock_async_session._result.scalar_one_or_none.return_value = sample_task
    now = datetime.now(timezone.utc)
    agent_id = uuid.uuid4()
    updated = await task_repo.update_task_status(
        mock_async_session,
        sample_task.id,
        status="COMPLETED",
        executor_agent_id=agent_id,
        executor_output_json='{"x": 1}',
        executor_confidence=0.95,
        execution_started_at=now,
        execution_completed_at=now,
        review_result_json='{"y": 2}',
        consensus_result="3_OF_3_APPROVE",
        review_completed_at=now,
        vertex_event_hash="h" * 64,
        vertex_round=5,
        vertex_finalised_at=now,
        completed_at=now,
        failed_at=now,
        failure_reason="x",
        escalated_at=now,
        escalation_reason="human reviewer flagged",
        retry_count=2,
    )
    assert updated is sample_task
    assert sample_task.status == "COMPLETED"
    assert sample_task.executor_confidence == 0.95
    assert sample_task.consensus_result == "3_OF_3_APPROVE"
    assert sample_task.vertex_round == 5
    assert sample_task.retry_count == 2


@pytest.mark.asyncio
async def test_update_task_status_minimal(mock_async_session, sample_task):
    mock_async_session._result.scalar_one_or_none.return_value = sample_task
    updated = await task_repo.update_task_status(
        mock_async_session, sample_task.id, status="EXECUTING",
    )
    assert updated is sample_task
    assert sample_task.status == "EXECUTING"


@pytest.mark.asyncio
async def test_update_task_status_not_found(mock_async_session):
    mock_async_session._result.scalar_one_or_none.return_value = None
    updated = await task_repo.update_task_status(
        mock_async_session, uuid.uuid4(), status="FAILED",
    )
    assert updated is None
