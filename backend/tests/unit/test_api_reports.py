"""Tests for app.api.v1.reports route handlers."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.v1 import reports as reports_api


@pytest.mark.asyncio
async def test_get_report_happy_path(mock_async_session, sample_task, sample_report):
    sample_report.vertex_event_hash = "h" * 64
    sample_report.generated_at = MagicMock()
    sample_report.generated_at.isoformat = MagicMock(return_value="2026-04-21T00:00:00")
    sample_task.vertex_finalised_at = MagicMock()
    sample_task.vertex_finalised_at.isoformat = MagicMock(return_value="2026-04-21T01:00:00")

    with patch.object(reports_api.task_repo, "get_task", AsyncMock(return_value=sample_task)), \
         patch.object(reports_api.report_repo, "get_report_by_task_id", AsyncMock(return_value=sample_report)):
        result = await reports_api.get_report(
            task_id=sample_task.id, _key_meta={}, session=mock_async_session,
        )
    assert result["schema_version"] == "poc_report_v1"
    assert result["report_available"] is True
    assert result["vertex_proof"]["event_hash"] == "h" * 64
    assert "eu_ai_act" in result


@pytest.mark.asyncio
async def test_get_report_task_not_found(mock_async_session):
    with patch.object(reports_api.task_repo, "get_task", AsyncMock(return_value=None)):
        with pytest.raises(HTTPException) as e:
            await reports_api.get_report(uuid.uuid4(), {}, mock_async_session)
    assert e.value.status_code == 404


@pytest.mark.asyncio
async def test_get_report_task_not_completed(mock_async_session, sample_task):
    sample_task.status = "QUEUED"
    with patch.object(reports_api.task_repo, "get_task", AsyncMock(return_value=sample_task)):
        with pytest.raises(HTTPException) as e:
            await reports_api.get_report(sample_task.id, {}, mock_async_session)
    assert e.value.status_code == 400


@pytest.mark.asyncio
async def test_get_report_missing_report(mock_async_session, sample_task):
    with patch.object(reports_api.task_repo, "get_task", AsyncMock(return_value=sample_task)), \
         patch.object(reports_api.report_repo, "get_report_by_task_id", AsyncMock(return_value=None)):
        with pytest.raises(HTTPException) as e:
            await reports_api.get_report(sample_task.id, {}, mock_async_session)
    assert e.value.status_code == 404


@pytest.mark.asyncio
async def test_get_report_bad_eu_ai_act_json(mock_async_session, sample_task, sample_report):
    sample_report.eu_ai_act_json = "not json"
    sample_report.generated_at = MagicMock()
    sample_report.generated_at.isoformat = MagicMock(return_value="2026-04-21T00:00:00")
    sample_task.vertex_finalised_at = None
    sample_report.vertex_event_hash = None
    with patch.object(reports_api.task_repo, "get_task", AsyncMock(return_value=sample_task)), \
         patch.object(reports_api.report_repo, "get_report_by_task_id", AsyncMock(return_value=sample_report)):
        result = await reports_api.get_report(sample_task.id, {}, mock_async_session)
    assert result["eu_ai_act"] == {}
    assert result["vertex_proof"] is None


@pytest.mark.asyncio
async def test_get_report_no_generated_at(mock_async_session, sample_task, sample_report):
    sample_report.generated_at = None
    sample_report.vertex_event_hash = None
    with patch.object(reports_api.task_repo, "get_task", AsyncMock(return_value=sample_task)), \
         patch.object(reports_api.report_repo, "get_report_by_task_id", AsyncMock(return_value=sample_report)):
        result = await reports_api.get_report(sample_task.id, {}, mock_async_session)
    assert result["generated_at"] is None


@pytest.mark.asyncio
async def test_export_report_happy_path(mock_async_session, sample_task, sample_report):
    sample_report.generated_at = MagicMock()
    sample_report.generated_at.isoformat = MagicMock(return_value="2026-04-21T00:00:00")
    sample_task.vertex_finalised_at = None

    with patch.object(reports_api.task_repo, "get_task", AsyncMock(return_value=sample_task)), \
         patch.object(reports_api.report_repo, "get_report_by_task_id", AsyncMock(return_value=sample_report)):
        result = await reports_api.export_report(
            task_id=sample_task.id, format="eu_ai_act",
            _key_meta={}, session=mock_async_session,
        )
    # EU AI Act keys should be merged at top level
    assert "article_9_risk_management" in result
    assert result["schema_version"] == "poc_report_v1"


@pytest.mark.asyncio
async def test_export_report_unsupported_format(mock_async_session):
    with pytest.raises(HTTPException) as e:
        await reports_api.export_report(
            task_id=uuid.uuid4(), format="xml",
            _key_meta={}, session=mock_async_session,
        )
    assert e.value.status_code == 400


@pytest.mark.asyncio
async def test_export_report_task_not_found(mock_async_session):
    with patch.object(reports_api.task_repo, "get_task", AsyncMock(return_value=None)):
        with pytest.raises(HTTPException) as e:
            await reports_api.export_report(uuid.uuid4(), "eu_ai_act", {}, mock_async_session)
    assert e.value.status_code == 404


@pytest.mark.asyncio
async def test_export_report_task_not_completed(mock_async_session, sample_task):
    sample_task.status = "EXECUTING"
    with patch.object(reports_api.task_repo, "get_task", AsyncMock(return_value=sample_task)):
        with pytest.raises(HTTPException) as e:
            await reports_api.export_report(sample_task.id, "eu_ai_act", {}, mock_async_session)
    assert e.value.status_code == 400


@pytest.mark.asyncio
async def test_export_report_missing_report(mock_async_session, sample_task):
    with patch.object(reports_api.task_repo, "get_task", AsyncMock(return_value=sample_task)), \
         patch.object(reports_api.report_repo, "get_report_by_task_id", AsyncMock(return_value=None)):
        with pytest.raises(HTTPException) as e:
            await reports_api.export_report(sample_task.id, "eu_ai_act", {}, mock_async_session)
    assert e.value.status_code == 404


@pytest.mark.asyncio
async def test_export_report_bad_json(mock_async_session, sample_task, sample_report):
    sample_report.eu_ai_act_json = "not json"
    sample_report.vertex_event_hash = None
    with patch.object(reports_api.task_repo, "get_task", AsyncMock(return_value=sample_task)), \
         patch.object(reports_api.report_repo, "get_report_by_task_id", AsyncMock(return_value=sample_report)):
        result = await reports_api.export_report(
            sample_task.id, "eu_ai_act", {}, mock_async_session,
        )
    # No article keys merged (eu_ai_act parsed to {})
    assert "article_9_risk_management" not in result
    assert "schema_version" in result
