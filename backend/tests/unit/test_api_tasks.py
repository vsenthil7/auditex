"""Tests for app.api.v1.tasks route handlers."""
from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.v1 import tasks as tasks_api
from app.models.task import TaskCreate


def test_vertex_mode_stub(monkeypatch):
    monkeypatch.setenv("USE_REAL_VERTEX", "false")
    assert tasks_api._vertex_mode() == "STUB"


def test_vertex_mode_live(monkeypatch):
    monkeypatch.setenv("USE_REAL_VERTEX", "true")
    assert tasks_api._vertex_mode() == "LIVE"


def test_orm_to_response_full(sample_task):
    resp = tasks_api._orm_to_response(sample_task)
    assert resp.task_id == sample_task.id
    assert resp.report_available is True
    assert resp.executor is not None
    assert resp.review is not None
    assert resp.vertex is not None


def test_orm_to_response_bad_json():
    t = MagicMock()
    t.id = uuid.uuid4()
    t.status = "QUEUED"
    t.task_type = "document_review"
    t.workflow_id = None
    t.executor_output_json = "not json"
    t.review_result_json = "also not json"
    t.vertex_event_hash = None
    t.report_available = False
    t.created_at = MagicMock()
    t.vertex_round = None
    t.vertex_finalised_at = None
    resp = tasks_api._orm_to_response(t)
    # Fallback: {"raw": "..."} for bad JSON
    assert resp.executor == {"raw": "not json"}
    assert resp.review == {"raw": "also not json"}


def test_orm_to_response_nulls():
    t = MagicMock()
    t.id = uuid.uuid4()
    t.status = "QUEUED"
    t.task_type = "document_review"
    t.workflow_id = None
    t.executor_output_json = None
    t.review_result_json = None
    t.vertex_event_hash = None
    t.report_available = False
    t.created_at = MagicMock()
    t.vertex_round = None
    t.vertex_finalised_at = None
    resp = tasks_api._orm_to_response(t)
    assert resp.executor is None
    assert resp.review is None
    assert resp.vertex is None


@pytest.mark.asyncio
async def test_submit_task_creates_and_dispatches(mock_async_session, sample_task):
    body = TaskCreate(
        task_type="document_review",
        payload={"x": 1},
        metadata={"submitted_by": "alice", "workflow_id": "wf1"},
    )
    with patch.object(tasks_api.task_repo, "create_task", AsyncMock(return_value=sample_task)), \
         patch.object(tasks_api, "celery_execute_task", MagicMock()) as mock_celery:
        mock_celery.delay = MagicMock()
        result = await tasks_api.submit_task(
            body, key_meta={"key_id": "k1"}, session=mock_async_session,
        )
    assert result["status"] == sample_task.status
    assert result["task_type"] == sample_task.task_type
    assert "message" in result
    mock_celery.delay.assert_called_once()


@pytest.mark.asyncio
async def test_submit_task_no_metadata(mock_async_session, sample_task):
    body = TaskCreate(task_type="document_review", payload={"x": 1})
    with patch.object(tasks_api.task_repo, "create_task", AsyncMock(return_value=sample_task)), \
         patch.object(tasks_api, "celery_execute_task", MagicMock()) as mock_celery:
        mock_celery.delay = MagicMock()
        result = await tasks_api.submit_task(
            body, key_meta={"key_id": "k1"}, session=mock_async_session,
        )
    assert result["task_id"] == str(sample_task.id)


@pytest.mark.asyncio
async def test_get_task_found(mock_async_session, sample_task):
    with patch.object(tasks_api.task_repo, "get_task", AsyncMock(return_value=sample_task)):
        result = await tasks_api.get_task(
            task_id=sample_task.id, _key_meta={"key_id": "k"}, session=mock_async_session,
        )
    assert result["task_id"] == str(sample_task.id)
    assert result["executor"] is not None
    assert result["review"] is not None
    assert result["vertex"] is not None


@pytest.mark.asyncio
async def test_get_task_404(mock_async_session):
    with patch.object(tasks_api.task_repo, "get_task", AsyncMock(return_value=None)):
        with pytest.raises(HTTPException) as e:
            await tasks_api.get_task(
                task_id=uuid.uuid4(), _key_meta={}, session=mock_async_session,
            )
    assert e.value.status_code == 404


@pytest.mark.asyncio
async def test_get_task_bad_json_fields(mock_async_session):
    t = MagicMock()
    t.id = uuid.uuid4()
    t.status = "COMPLETED"
    t.task_type = "document_review"
    t.workflow_id = "wf1"
    t.executor_output_json = "not json"
    t.review_result_json = "not json either"
    t.vertex_event_hash = None
    t.vertex_round = None
    t.vertex_finalised_at = None
    t.created_at = MagicMock()
    t.created_at.isoformat.return_value = "2026-04-21T00:00:00"
    t.report_available = True

    with patch.object(tasks_api.task_repo, "get_task", AsyncMock(return_value=t)):
        result = await tasks_api.get_task(t.id, {}, mock_async_session)
    # Bad JSON → None on both
    assert result["executor"] is None
    assert result["review"] is None
    assert result["vertex"] is None


@pytest.mark.asyncio
async def test_get_task_with_vertex(mock_async_session, sample_task):
    sample_task.created_at.isoformat = MagicMock(return_value="2026-04-21T00:00:00")
    sample_task.vertex_finalised_at.isoformat = MagicMock(return_value="2026-04-21T01:00:00")
    with patch.object(tasks_api.task_repo, "get_task", AsyncMock(return_value=sample_task)):
        result = await tasks_api.get_task(sample_task.id, {}, mock_async_session)
    assert result["vertex"]["event_hash"] == sample_task.vertex_event_hash
    assert result["vertex"]["round"] == sample_task.vertex_round


@pytest.mark.asyncio
async def test_list_tasks(mock_async_session, sample_task):
    sample_task.created_at.isoformat = MagicMock(return_value="2026-04-21T00:00:00")
    with patch.object(
        tasks_api.task_repo, "list_tasks", AsyncMock(return_value=([sample_task], 1)),
    ):
        result = await tasks_api.list_tasks(
            page=1, page_size=20, status_filter=None,
            _key_meta={}, session=mock_async_session,
        )
    assert result["total"] == 1
    assert len(result["tasks"]) == 1
    assert result["page"] == 1


@pytest.mark.asyncio
async def test_list_tasks_with_filter(mock_async_session, sample_task):
    sample_task.created_at.isoformat = MagicMock(return_value="2026-04-21T00:00:00")
    with patch.object(
        tasks_api.task_repo, "list_tasks", AsyncMock(return_value=([sample_task], 1)),
    ):
        result = await tasks_api.list_tasks(
            page=2, page_size=5, status_filter="COMPLETED",
            _key_meta={}, session=mock_async_session,
        )
    assert result["page"] == 2
    assert result["page_size"] == 5
