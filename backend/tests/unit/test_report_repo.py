"""Tests for db.repositories.report_repo."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from db.repositories import report_repo


@pytest.mark.asyncio
async def test_create_report(mock_async_session):
    task_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    report = await report_repo.create_report(
        mock_async_session,
        task_id=task_id,
        narrative="Plain-English summary.",
        eu_ai_act_json='{"article_9_risk_management": {}}',
        schema_version="poc_report_v1",
        vertex_event_hash="h" * 64,
        generated_at=now,
        generator_model="claude-sonnet-4-6",
    )
    assert report.task_id == task_id
    assert report.narrative.startswith("Plain")
    assert report.schema_version == "poc_report_v1"
    mock_async_session.add.assert_called_once()
    mock_async_session.flush.assert_awaited()


@pytest.mark.asyncio
async def test_create_report_default_schema_version(mock_async_session):
    report = await report_repo.create_report(
        mock_async_session,
        task_id=uuid.uuid4(),
        narrative="x",
        eu_ai_act_json="{}",
        generated_at=datetime.now(timezone.utc),
        generator_model="claude",
    )
    assert report.schema_version == "poc_report_v1"


@pytest.mark.asyncio
async def test_get_report_by_task_id_found(mock_async_session, sample_report):
    mock_async_session._result.scalar_one_or_none.return_value = sample_report
    r = await report_repo.get_report_by_task_id(mock_async_session, sample_report.task_id)
    assert r is sample_report


@pytest.mark.asyncio
async def test_get_report_by_task_id_not_found(mock_async_session):
    mock_async_session._result.scalar_one_or_none.return_value = None
    r = await report_repo.get_report_by_task_id(mock_async_session, uuid.uuid4())
    assert r is None
