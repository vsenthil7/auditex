"""Tests for workers.reporting_worker."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from workers import reporting_worker


def _make_session():
    s = AsyncMock()
    s.commit = AsyncMock()
    s.flush = AsyncMock()
    return s


def _make_factory(session):
    factory_ctx = MagicMock()
    factory_ctx.__aenter__ = AsyncMock(return_value=session)
    factory_ctx.__aexit__ = AsyncMock(return_value=None)
    return MagicMock(return_value=factory_ctx)


def _make_task(status="COMPLETED"):
    t = MagicMock()
    t.id = uuid.uuid4()
    t.status = status
    t.task_type = "document_review"
    t.executor_output_json = '{"model": "claude", "output": {"recommendation": "APPROVE"}, "confidence": 0.9}'
    t.review_result_json = '{"consensus": "3_OF_3_APPROVE", "reviewers": []}'
    t.vertex_event_hash = "h" * 64
    t.vertex_round = 1
    t.vertex_finalised_at = datetime.now(timezone.utc)
    t.report_available = False
    return t


def _poc():
    return SimpleNamespace(
        plain_english_summary="Narrative text.",
        generated_at=datetime.now(timezone.utc),
    )


def _make_celery_task_mock():
    ct = MagicMock()
    ct.retry = MagicMock(side_effect=RuntimeError("retry called"))
    return ct


def test_make_engine_and_session_returns_tuple():
    engine, factory = reporting_worker._make_engine_and_session()
    assert engine is not None
    assert factory is not None


def test_generate_poc_report_is_celery_task():
    assert hasattr(reporting_worker.generate_poc_report, "delay")


def test_generate_poc_report_sync_wrapper_success():
    """Cover the Celery-entry sync wrapper (lines 77-92): new event loop +
    engine setup + run_until_complete + dispose cleanup."""
    fake_engine = MagicMock()
    fake_engine.dispose = AsyncMock()
    fake_factory = MagicMock()

    async def fake_coro(*args, **kwargs):
        return {"task_id": "x", "outcome": "GENERATED"}

    with patch.object(
        reporting_worker, "_make_engine_and_session",
        return_value=(fake_engine, fake_factory),
    ), patch.object(
        reporting_worker, "_generate_report_async", side_effect=fake_coro,
    ):
        out = reporting_worker.generate_poc_report.__wrapped__("some-task-id")
    assert out["outcome"] == "GENERATED"
    fake_engine.dispose.assert_called()


def test_generate_poc_report_sync_wrapper_dispose_error_swallowed():
    """Cover the `except Exception` branch in the finally block where
    engine.dispose() itself raises."""
    fake_engine = MagicMock()
    fake_engine.dispose = AsyncMock(side_effect=RuntimeError("dispose boom"))
    fake_factory = MagicMock()

    async def fake_coro(*args, **kwargs):
        return {"task_id": "x", "outcome": "GENERATED"}

    with patch.object(
        reporting_worker, "_make_engine_and_session",
        return_value=(fake_engine, fake_factory),
    ), patch.object(
        reporting_worker, "_generate_report_async", side_effect=fake_coro,
    ):
        out = reporting_worker.generate_poc_report.__wrapped__("some-task-id")
    assert out["outcome"] == "GENERATED"


@pytest.mark.asyncio
async def test_generate_report_async_task_not_found():
    session = _make_session()
    factory = _make_factory(session)
    with patch("db.repositories.task_repo.get_task", AsyncMock(return_value=None)):
        out = await reporting_worker._generate_report_async(
            _make_celery_task_mock(), str(uuid.uuid4()), factory,
        )
    assert out["outcome"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_generate_report_async_not_completed():
    task = _make_task(status="EXECUTING")
    session = _make_session()
    factory = _make_factory(session)
    with patch("db.repositories.task_repo.get_task", AsyncMock(return_value=task)):
        out = await reporting_worker._generate_report_async(
            _make_celery_task_mock(), str(task.id), factory,
        )
    assert out["outcome"] == "SKIPPED"


@pytest.mark.asyncio
async def test_generate_report_async_already_exists():
    task = _make_task()
    session = _make_session()
    factory = _make_factory(session)
    existing = MagicMock()
    with patch("db.repositories.task_repo.get_task", AsyncMock(return_value=task)), \
         patch("db.repositories.report_repo.get_report_by_task_id",
               AsyncMock(return_value=existing)):
        out = await reporting_worker._generate_report_async(
            _make_celery_task_mock(), str(task.id), factory,
        )
    assert out["outcome"] == "ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_generate_report_async_happy_path():
    task = _make_task()
    session = _make_session()
    factory = _make_factory(session)
    fake_report = MagicMock()
    fake_report.id = uuid.uuid4()

    with patch("db.repositories.task_repo.get_task", AsyncMock(return_value=task)), \
         patch("db.repositories.report_repo.get_report_by_task_id",
               AsyncMock(return_value=None)), \
         patch("core.reporting.poc_generator.generate_report",
               AsyncMock(return_value=_poc())), \
         patch("core.reporting.eu_act_formatter.format_eu_ai_act",
               MagicMock(return_value={"article_9_risk_management": {}})), \
         patch("db.repositories.report_repo.create_report",
               AsyncMock(return_value=fake_report)):
        out = await reporting_worker._generate_report_async(
            _make_celery_task_mock(), str(task.id), factory,
        )
    assert out["outcome"] == "GENERATED"
    assert task.report_available is True


@pytest.mark.asyncio
async def test_generate_report_async_narrative_failure_triggers_retry():
    task = _make_task()
    session = _make_session()
    factory = _make_factory(session)
    ct = _make_celery_task_mock()

    with patch("db.repositories.task_repo.get_task", AsyncMock(return_value=task)), \
         patch("db.repositories.report_repo.get_report_by_task_id",
               AsyncMock(return_value=None)), \
         patch("core.reporting.poc_generator.generate_report",
               AsyncMock(side_effect=RuntimeError("claude dead"))):
        with pytest.raises(RuntimeError):  # our celery.retry side_effect raises RuntimeError
            await reporting_worker._generate_report_async(ct, str(task.id), factory)


@pytest.mark.asyncio
async def test_generate_report_async_bad_executor_json():
    task = _make_task()
    task.executor_output_json = "not json at all"
    task.review_result_json = "also not json"
    session = _make_session()
    factory = _make_factory(session)
    fake_report = MagicMock()
    fake_report.id = uuid.uuid4()

    with patch("db.repositories.task_repo.get_task", AsyncMock(return_value=task)), \
         patch("db.repositories.report_repo.get_report_by_task_id",
               AsyncMock(return_value=None)), \
         patch("core.reporting.poc_generator.generate_report",
               AsyncMock(return_value=_poc())), \
         patch("core.reporting.eu_act_formatter.format_eu_ai_act",
               MagicMock(return_value={})), \
         patch("db.repositories.report_repo.create_report",
               AsyncMock(return_value=fake_report)):
        out = await reporting_worker._generate_report_async(
            _make_celery_task_mock(), str(task.id), factory,
        )
    assert out["outcome"] == "GENERATED"


@pytest.mark.asyncio
async def test_generate_report_async_no_vertex_finalised_at():
    task = _make_task()
    task.vertex_finalised_at = None
    session = _make_session()
    factory = _make_factory(session)
    fake_report = MagicMock()
    fake_report.id = uuid.uuid4()

    with patch("db.repositories.task_repo.get_task", AsyncMock(return_value=task)), \
         patch("db.repositories.report_repo.get_report_by_task_id",
               AsyncMock(return_value=None)), \
         patch("core.reporting.poc_generator.generate_report",
               AsyncMock(return_value=_poc())), \
         patch("core.reporting.eu_act_formatter.format_eu_ai_act",
               MagicMock(return_value={})), \
         patch("db.repositories.report_repo.create_report",
               AsyncMock(return_value=fake_report)):
        out = await reporting_worker._generate_report_async(
            _make_celery_task_mock(), str(task.id), factory,
        )
    assert out["outcome"] == "GENERATED"
