"""Tests for workers.execution_worker."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from workers import execution_worker


def _make_celery_task_mock(retries=0):
    ct = MagicMock()
    ct.request.retries = retries
    ct.retry = MagicMock(side_effect=RuntimeError("retry called"))
    return ct


def _make_session_factory(session):
    factory_ctx = MagicMock()
    factory_ctx.__aenter__ = AsyncMock(return_value=session)
    factory_ctx.__aexit__ = AsyncMock(return_value=None)
    return MagicMock(return_value=factory_ctx)


def _make_session():
    s = AsyncMock()
    s.commit = AsyncMock()
    s.rollback = AsyncMock()
    s.close = AsyncMock()
    return s


def _make_task_orm(status="QUEUED", task_id=None):
    t = MagicMock()
    t.id = task_id or uuid.uuid4()
    t.status = status
    t.task_type = "document_review"
    t.payload_json = json.dumps({"payload": {"doc": "x"}})
    return t


def _make_executor_result():
    er = MagicMock()
    er.model = "claude-sonnet-4-6"
    er.output = {"recommendation": "APPROVE"}
    er.confidence = 0.9
    er.reasoning = "ok"
    er.tokens_used = 100
    return er


def _make_review_result():
    rr = SimpleNamespace(
        consensus="3_OF_3_APPROVE",
        reviewers=[
            SimpleNamespace(model="gpt-4o", verdict="APPROVE", reasoning="r",
                            confidence=0.9, committed_hash="h1",
                            commitment_verified=True, nonce="n1"),
            SimpleNamespace(model="gpt-4o", verdict="APPROVE", reasoning="r",
                            confidence=0.88, committed_hash="h2",
                            commitment_verified=True, nonce="n2"),
            SimpleNamespace(model="claude", verdict="APPROVE", reasoning="r",
                            confidence=0.85, committed_hash="h3",
                            commitment_verified=True, nonce="n3"),
        ],
        verdicts=["APPROVE", "APPROVE", "APPROVE"],
        all_verified=True,
        completed_at="2026-04-21T01:00:00+00:00",
    )
    return rr


def _receipt():
    return SimpleNamespace(
        event_hash="h" * 64,
        round=5,
        finalised_at="2026-04-21T01:00:00+00:00",
        is_stub=True,
        foxmq_timestamp=None,
    )


@pytest.mark.asyncio
async def test_execute_task_async_task_not_found():
    session = _make_session()
    factory = _make_session_factory(session)
    with patch("db.repositories.task_repo.get_task", AsyncMock(return_value=None)):
        out = await execution_worker._execute_task_async(
            _make_celery_task_mock(), str(uuid.uuid4()), factory,
        )
    assert out["status"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_execute_task_async_already_completed():
    task = _make_task_orm(status="COMPLETED")
    session = _make_session()
    factory = _make_session_factory(session)
    with patch("db.repositories.task_repo.get_task", AsyncMock(return_value=task)):
        out = await execution_worker._execute_task_async(
            _make_celery_task_mock(), str(task.id), factory,
        )
    assert out["status"] == "COMPLETED"


@pytest.mark.asyncio
async def test_execute_task_async_bad_payload_routes_to_dlq():
    task = _make_task_orm()
    task.payload_json = "not json at all"
    session = _make_session()
    factory = _make_session_factory(session)
    with patch("db.repositories.task_repo.get_task", AsyncMock(return_value=task)), \
         patch("db.repositories.task_repo.update_task_status", AsyncMock()), \
         patch("db.repositories.event_repo.insert_event", AsyncMock()), \
         patch("db.repositories.human_oversight_repo.get_policy", AsyncMock(return_value=None)), \
         patch("core.execution.retry_handler.route_to_dlq", AsyncMock()) as m_dlq:
        out = await execution_worker._execute_task_async(
            _make_celery_task_mock(), str(task.id), factory,
        )
    assert out["status"] == "FAILED"
    m_dlq.assert_awaited()


@pytest.mark.asyncio
async def test_execute_task_async_happy_path_stub_mode(monkeypatch):
    monkeypatch.setenv("USE_REAL_VERTEX", "false")
    task = _make_task_orm()
    session = _make_session()
    factory = _make_session_factory(session)

    with patch("db.repositories.task_repo.get_task", AsyncMock(return_value=task)), \
         patch("db.repositories.task_repo.update_task_status", AsyncMock()), \
         patch("db.repositories.event_repo.insert_event", AsyncMock()), \
         patch("db.repositories.human_oversight_repo.get_policy", AsyncMock(return_value=None)), \
         patch("core.execution.claude_executor.execute_task",
               AsyncMock(return_value=_make_executor_result())), \
         patch("core.review.coordinator.run_review_pipeline",
               AsyncMock(return_value=_make_review_result())), \
         patch("core.consensus.event_builder.build_task_completed_event",
               MagicMock(return_value={"event_type": "task_completed"})), \
         patch("core.consensus.foxmq_client.publish_event", MagicMock(return_value=True)), \
         patch("core.consensus.vertex_client.submit_event",
               MagicMock(return_value=_receipt())), \
         patch("asyncio.sleep", AsyncMock()), \
         patch("workers.reporting_worker.generate_poc_report") as mock_report:
        mock_report.delay = MagicMock()
        out = await execution_worker._execute_task_async(
            _make_celery_task_mock(), str(task.id), factory,
        )
    assert out["status"] == "COMPLETED"


@pytest.mark.asyncio
async def test_execute_task_async_claude_value_error_retries():
    task = _make_task_orm()
    session = _make_session()
    factory = _make_session_factory(session)
    ct = _make_celery_task_mock(retries=0)

    with patch("db.repositories.task_repo.get_task", AsyncMock(return_value=task)), \
         patch("db.repositories.task_repo.update_task_status", AsyncMock()), \
         patch("db.repositories.event_repo.insert_event", AsyncMock()), \
         patch("db.repositories.human_oversight_repo.get_policy", AsyncMock(return_value=None)), \
         patch("core.execution.claude_executor.execute_task",
               AsyncMock(side_effect=ValueError("bad json"))), \
         patch("core.execution.retry_handler.exponential_backoff", AsyncMock()):
        with pytest.raises(RuntimeError):  # our mock retry raises RuntimeError
            await execution_worker._execute_task_async(ct, str(task.id), factory)


@pytest.mark.asyncio
async def test_execute_task_async_claude_fails_max_retries():
    task = _make_task_orm()
    session = _make_session()
    factory = _make_session_factory(session)
    ct = _make_celery_task_mock(retries=3)  # already at max

    with patch("db.repositories.task_repo.get_task", AsyncMock(return_value=task)), \
         patch("db.repositories.task_repo.update_task_status", AsyncMock()), \
         patch("db.repositories.event_repo.insert_event", AsyncMock()), \
         patch("db.repositories.human_oversight_repo.get_policy", AsyncMock(return_value=None)), \
         patch("core.execution.claude_executor.execute_task",
               AsyncMock(side_effect=ValueError("bad json"))), \
         patch("core.execution.retry_handler.route_to_dlq", AsyncMock()) as m_dlq:
        out = await execution_worker._execute_task_async(ct, str(task.id), factory)
    assert out["status"] == "FAILED"
    m_dlq.assert_awaited()


@pytest.mark.asyncio
async def test_execute_task_async_unexpected_exception_dlq():
    task = _make_task_orm()
    session = _make_session()
    factory = _make_session_factory(session)

    with patch("db.repositories.task_repo.get_task", AsyncMock(return_value=task)), \
         patch("db.repositories.task_repo.update_task_status", AsyncMock()), \
         patch("db.repositories.event_repo.insert_event", AsyncMock()), \
         patch("db.repositories.human_oversight_repo.get_policy", AsyncMock(return_value=None)), \
         patch("core.execution.claude_executor.execute_task",
               AsyncMock(side_effect=RuntimeError("kaboom"))), \
         patch("core.execution.retry_handler.route_to_dlq", AsyncMock()) as m_dlq:
        out = await execution_worker._execute_task_async(
            _make_celery_task_mock(retries=0), str(task.id), factory,
        )
    assert out["status"] == "FAILED"
    m_dlq.assert_awaited()


@pytest.mark.asyncio
async def test_execute_task_async_security_violation():
    from core.review.hash_commitment import SecurityViolationError
    task = _make_task_orm()
    session = _make_session()
    factory = _make_session_factory(session)

    with patch("db.repositories.task_repo.get_task", AsyncMock(return_value=task)), \
         patch("db.repositories.task_repo.update_task_status", AsyncMock()), \
         patch("db.repositories.event_repo.insert_event", AsyncMock()), \
         patch("db.repositories.human_oversight_repo.get_policy", AsyncMock(return_value=None)), \
         patch("core.execution.claude_executor.execute_task",
               AsyncMock(return_value=_make_executor_result())), \
         patch("core.review.coordinator.run_review_pipeline",
               AsyncMock(side_effect=SecurityViolationError("hash mismatch"))), \
         patch("core.execution.retry_handler.route_to_dlq", AsyncMock()) as m_dlq:
        out = await execution_worker._execute_task_async(
            _make_celery_task_mock(), str(task.id), factory,
        )
    assert out["status"] == "FAILED"
    m_dlq.assert_awaited()


@pytest.mark.asyncio
async def test_execute_task_async_review_pipeline_exception():
    task = _make_task_orm()
    session = _make_session()
    factory = _make_session_factory(session)

    with patch("db.repositories.task_repo.get_task", AsyncMock(return_value=task)), \
         patch("db.repositories.task_repo.update_task_status", AsyncMock()), \
         patch("db.repositories.event_repo.insert_event", AsyncMock()), \
         patch("db.repositories.human_oversight_repo.get_policy", AsyncMock(return_value=None)), \
         patch("core.execution.claude_executor.execute_task",
               AsyncMock(return_value=_make_executor_result())), \
         patch("core.review.coordinator.run_review_pipeline",
               AsyncMock(side_effect=RuntimeError("review boom"))), \
         patch("core.execution.retry_handler.route_to_dlq", AsyncMock()) as m_dlq:
        out = await execution_worker._execute_task_async(
            _make_celery_task_mock(), str(task.id), factory,
        )
    assert out["status"] == "FAILED"


@pytest.mark.asyncio
async def test_execute_task_async_consensus_error_continues(monkeypatch):
    """Consensus layer failure must not block task completion."""
    monkeypatch.setenv("USE_REAL_VERTEX", "false")
    task = _make_task_orm()
    session = _make_session()
    factory = _make_session_factory(session)

    with patch("db.repositories.task_repo.get_task", AsyncMock(return_value=task)), \
         patch("db.repositories.task_repo.update_task_status", AsyncMock()), \
         patch("db.repositories.event_repo.insert_event", AsyncMock()), \
         patch("db.repositories.human_oversight_repo.get_policy", AsyncMock(return_value=None)), \
         patch("core.execution.claude_executor.execute_task",
               AsyncMock(return_value=_make_executor_result())), \
         patch("core.review.coordinator.run_review_pipeline",
               AsyncMock(return_value=_make_review_result())), \
         patch("core.consensus.event_builder.build_task_completed_event",
               MagicMock(side_effect=RuntimeError("consensus boom"))), \
         patch("asyncio.sleep", AsyncMock()), \
         patch("workers.reporting_worker.generate_poc_report") as mock_report:
        mock_report.delay = MagicMock()
        out = await execution_worker._execute_task_async(
            _make_celery_task_mock(), str(task.id), factory,
        )
    # Still COMPLETED because consensus errors are non-blocking
    assert out["status"] == "COMPLETED"


@pytest.mark.asyncio
async def test_execute_task_async_reporting_dispatch_fails(monkeypatch):
    monkeypatch.setenv("USE_REAL_VERTEX", "false")
    task = _make_task_orm()
    session = _make_session()
    factory = _make_session_factory(session)

    with patch("db.repositories.task_repo.get_task", AsyncMock(return_value=task)), \
         patch("db.repositories.task_repo.update_task_status", AsyncMock()), \
         patch("db.repositories.event_repo.insert_event", AsyncMock()), \
         patch("db.repositories.human_oversight_repo.get_policy", AsyncMock(return_value=None)), \
         patch("core.execution.claude_executor.execute_task",
               AsyncMock(return_value=_make_executor_result())), \
         patch("core.review.coordinator.run_review_pipeline",
               AsyncMock(return_value=_make_review_result())), \
         patch("core.consensus.event_builder.build_task_completed_event",
               MagicMock(return_value={"event_type": "task_completed"})), \
         patch("core.consensus.foxmq_client.publish_event", MagicMock(return_value=True)), \
         patch("core.consensus.vertex_client.submit_event",
               MagicMock(return_value=_receipt())), \
         patch("asyncio.sleep", AsyncMock()), \
         patch("workers.reporting_worker.generate_poc_report") as mock_report:
        mock_report.delay = MagicMock(side_effect=RuntimeError("reporting dispatch down"))
        out = await execution_worker._execute_task_async(
            _make_celery_task_mock(), str(task.id), factory,
        )
    # Still COMPLETED — dispatch failure is swallowed
    assert out["status"] == "COMPLETED"


def test_make_engine_and_session_returns_tuple():
    engine, factory = execution_worker._make_engine_and_session()
    assert engine is not None
    assert factory is not None


def test_execute_task_is_celery_task():
    # execute_task is the registered Celery task
    assert hasattr(execution_worker.execute_task, "delay")
    assert hasattr(execution_worker.execute_task, "apply_async")


def test_execute_task_sync_wrapper_success():
    """Cover the Celery-entry sync wrapper (lines 79-94): new event loop +
    engine setup + run_until_complete + dispose cleanup."""
    fake_engine = MagicMock()
    fake_engine.dispose = AsyncMock()
    fake_factory = MagicMock()

    async def fake_coro(*args, **kwargs):
        return {"task_id": "x", "status": "COMPLETED"}

    with patch.object(
        execution_worker, "_make_engine_and_session",
        return_value=(fake_engine, fake_factory),
    ), patch.object(
        execution_worker, "_execute_task_async", side_effect=fake_coro,
    ):
        # Celery bound task: __wrapped__ is already bound to `self`, so just
        # pass task_id. Call `apply(args=[...]).get()` for safer invocation.
        out = execution_worker.execute_task.__wrapped__("some-task-id")
    assert out["status"] == "COMPLETED"
    fake_engine.dispose.assert_called()  # verify cleanup happened


def test_execute_task_sync_wrapper_dispose_error_swallowed():
    """Cover the `except Exception as e:` branch in the finally block where
    engine.dispose() itself raises."""
    fake_engine = MagicMock()
    fake_engine.dispose = AsyncMock(side_effect=RuntimeError("dispose boom"))
    fake_factory = MagicMock()

    async def fake_coro(*args, **kwargs):
        return {"task_id": "x", "status": "COMPLETED"}

    with patch.object(
        execution_worker, "_make_engine_and_session",
        return_value=(fake_engine, fake_factory),
    ), patch.object(
        execution_worker, "_execute_task_async", side_effect=fake_coro,
    ):
        out = execution_worker.execute_task.__wrapped__("some-task-id")
    # Still returns the inner result even though dispose raised
    assert out["status"] == "COMPLETED"
