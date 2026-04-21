"""Tests for app.models.task pydantic schemas (HTTP layer)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.models.task import TaskCreate, TaskListResponse, TaskResponse, TaskStatus


def test_task_status_values():
    assert TaskStatus.QUEUED.value == "QUEUED"
    assert TaskStatus.COMPLETED.value == "COMPLETED"
    assert TaskStatus.FAILED.value == "FAILED"
    assert TaskStatus.EXECUTING.value == "EXECUTING"
    assert TaskStatus.REVIEWING.value == "REVIEWING"
    assert TaskStatus.FINALISING.value == "FINALISING"
    assert TaskStatus.ESCALATED.value == "ESCALATED"


def test_task_create_valid():
    t = TaskCreate(task_type="document_review", payload={"a": 1})
    assert t.task_type == "document_review"
    assert t.payload == {"a": 1}
    assert t.metadata is None


def test_task_create_with_metadata():
    t = TaskCreate(
        task_type="risk_analysis",
        payload={"doc": "x"},
        metadata={"submitted_by": "alice", "workflow_id": "wf1"},
    )
    assert t.metadata["submitted_by"] == "alice"


def test_task_create_task_type_empty_raises():
    with pytest.raises(ValidationError):
        TaskCreate(task_type="", payload={})


def test_task_create_task_type_too_long():
    with pytest.raises(ValidationError):
        TaskCreate(task_type="x" * 200, payload={})


def test_task_response_minimal():
    r = TaskResponse(
        task_id=uuid.uuid4(),
        status=TaskStatus.QUEUED,
        task_type="document_review",
        created_at=datetime.now(timezone.utc),
    )
    assert r.executor is None
    assert r.review is None
    assert r.vertex is None
    assert r.report_available is False


def test_task_response_full():
    r = TaskResponse(
        task_id=uuid.uuid4(),
        status=TaskStatus.COMPLETED,
        task_type="risk_analysis",
        workflow_id="wf1",
        created_at=datetime.now(timezone.utc),
        executor={"model": "claude"},
        review={"consensus": "3_OF_3_APPROVE"},
        vertex={"event_hash": "abc"},
        report_available=True,
    )
    assert r.report_available is True


def test_task_list_response_shape():
    tr = TaskResponse(
        task_id=uuid.uuid4(),
        status=TaskStatus.QUEUED,
        task_type="document_review",
        created_at=datetime.now(timezone.utc),
    )
    lst = TaskListResponse(tasks=[tr], total=1, page=1, page_size=20)
    assert lst.total == 1
    assert len(lst.tasks) == 1
