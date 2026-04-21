"""Tests for app.api.v1.reports route handlers."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.v1 import reports as reports_api
from app.config import settings
from core.reporting import export_signer


# --------------------------------------------------------------------------- #
# Fixtures: signing key setup
# --------------------------------------------------------------------------- #
@pytest.fixture
def with_signing_key(monkeypatch):
    """Configure a working HMAC key for sign/verify paths."""
    monkeypatch.setattr(settings, "EXPORT_SIGNING_KEYS", "")
    monkeypatch.setattr(settings, "EXPORT_SIGNING_KEY_ID", "api-test-key")
    monkeypatch.setattr(settings, "EXPORT_SIGNING_KEY_HEX", "aa" * 32)
    return monkeypatch


@pytest.fixture
def without_signing_key(monkeypatch):
    """Blank out all signing env so sign_export raises SigningKeyNotConfigured."""
    monkeypatch.setattr(settings, "EXPORT_SIGNING_KEYS", "")
    monkeypatch.setattr(settings, "EXPORT_SIGNING_KEY_ID", "")
    monkeypatch.setattr(settings, "EXPORT_SIGNING_KEY_HEX", "")
    return monkeypatch


def _tidy_report(report):
    """
    sample_report from conftest has MagicMock attrs that are truthy by default.
    For the unsigned view tests we need org_signature to be falsy.
    Call this to reset signature-related attrs to None unless a test overrides.
    """
    report.org_signature = None
    report.signing_key_id = None
    report.signed_at = None
    return report


def _tidy_task(task):
    """Ensure task.vertex_finalised_at is controllable."""
    # conftest already sets vertex_finalised_at to a MagicMock with isoformat
    return task


# --------------------------------------------------------------------------- #
# GET /reports/{task_id}
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_get_report_happy_path(mock_async_session, sample_task, sample_report):
    _tidy_report(sample_report)
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
    assert result["signature"] is None


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
    _tidy_report(sample_report)
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
    _tidy_report(sample_report)
    sample_report.generated_at = None
    sample_report.vertex_event_hash = None
    with patch.object(reports_api.task_repo, "get_task", AsyncMock(return_value=sample_task)), \
         patch.object(reports_api.report_repo, "get_report_by_task_id", AsyncMock(return_value=sample_report)):
        result = await reports_api.get_report(sample_task.id, {}, mock_async_session)
    assert result["generated_at"] is None


@pytest.mark.asyncio
async def test_get_report_empty_eu_ai_act_json(mock_async_session, sample_task, sample_report):
    """report.eu_ai_act_json is empty string / None -> branch that returns {}."""
    _tidy_report(sample_report)
    sample_report.eu_ai_act_json = None
    sample_report.vertex_event_hash = None
    sample_report.generated_at = None
    with patch.object(reports_api.task_repo, "get_task", AsyncMock(return_value=sample_task)), \
         patch.object(reports_api.report_repo, "get_report_by_task_id", AsyncMock(return_value=sample_report)):
        result = await reports_api.get_report(sample_task.id, {}, mock_async_session)
    assert result["eu_ai_act"] == {}


@pytest.mark.asyncio
async def test_get_report_includes_stored_signature_when_signed(
    mock_async_session, sample_task, sample_report
):
    _tidy_report(sample_report)
    sample_report.org_signature = "de" * 32
    sample_report.signing_key_id = "api-test-key"
    sample_report.signed_at = MagicMock()
    sample_report.signed_at.isoformat = MagicMock(return_value="2026-04-21T22:00:00+00:00")
    sample_report.generated_at = None
    sample_report.vertex_event_hash = None
    with patch.object(reports_api.task_repo, "get_task", AsyncMock(return_value=sample_task)), \
         patch.object(reports_api.report_repo, "get_report_by_task_id", AsyncMock(return_value=sample_report)):
        result = await reports_api.get_report(sample_task.id, {}, mock_async_session)
    sig = result["signature"]
    assert sig is not None
    assert sig["algorithm"] == "HMAC-SHA256"
    assert sig["signing_key_id"] == "api-test-key"
    assert sig["signature_hex"] == "de" * 32
    assert sig["signed_at"] == "2026-04-21T22:00:00+00:00"


@pytest.mark.asyncio
async def test_get_report_stored_signature_no_signed_at(
    mock_async_session, sample_task, sample_report
):
    """Covers the signed_at is None branch in _stored_signature_of."""
    _tidy_report(sample_report)
    sample_report.org_signature = "ab" * 32
    sample_report.signing_key_id = "api-test-key"
    sample_report.signed_at = None
    sample_report.generated_at = None
    sample_report.vertex_event_hash = None
    with patch.object(reports_api.task_repo, "get_task", AsyncMock(return_value=sample_task)), \
         patch.object(reports_api.report_repo, "get_report_by_task_id", AsyncMock(return_value=sample_report)):
        result = await reports_api.get_report(sample_task.id, {}, mock_async_session)
    assert result["signature"]["signed_at"] is None


# --------------------------------------------------------------------------- #
# GET /reports/{task_id}/export (unsigned path)
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_export_report_happy_path(mock_async_session, sample_task, sample_report):
    _tidy_report(sample_report)
    sample_report.generated_at = MagicMock()
    sample_report.generated_at.isoformat = MagicMock(return_value="2026-04-21T00:00:00")
    sample_task.vertex_finalised_at = None

    with patch.object(reports_api.task_repo, "get_task", AsyncMock(return_value=sample_task)), \
         patch.object(reports_api.report_repo, "get_report_by_task_id", AsyncMock(return_value=sample_report)):
        result = await reports_api.export_report(
            task_id=sample_task.id, format="eu_ai_act", signed=False,
            _key_meta={}, session=mock_async_session,
        )
    assert "article_9_risk_management" in result
    assert result["schema_version"] == "poc_report_v1"
    # Unsigned path returns flat payload (NO schema/payload envelope wrapping)
    assert "schema" not in result or result.get("schema") == "poc_report_v1"


@pytest.mark.asyncio
async def test_export_report_unsupported_format(mock_async_session):
    with pytest.raises(HTTPException) as e:
        await reports_api.export_report(
            task_id=uuid.uuid4(), format="xml", signed=False,
            _key_meta={}, session=mock_async_session,
        )
    assert e.value.status_code == 400


@pytest.mark.asyncio
async def test_export_report_task_not_found(mock_async_session):
    with patch.object(reports_api.task_repo, "get_task", AsyncMock(return_value=None)):
        with pytest.raises(HTTPException) as e:
            await reports_api.export_report(uuid.uuid4(), "eu_ai_act", False, {}, mock_async_session)
    assert e.value.status_code == 404


@pytest.mark.asyncio
async def test_export_report_task_not_completed(mock_async_session, sample_task):
    sample_task.status = "EXECUTING"
    with patch.object(reports_api.task_repo, "get_task", AsyncMock(return_value=sample_task)):
        with pytest.raises(HTTPException) as e:
            await reports_api.export_report(sample_task.id, "eu_ai_act", False, {}, mock_async_session)
    assert e.value.status_code == 400


@pytest.mark.asyncio
async def test_export_report_missing_report(mock_async_session, sample_task):
    with patch.object(reports_api.task_repo, "get_task", AsyncMock(return_value=sample_task)), \
         patch.object(reports_api.report_repo, "get_report_by_task_id", AsyncMock(return_value=None)):
        with pytest.raises(HTTPException) as e:
            await reports_api.export_report(sample_task.id, "eu_ai_act", False, {}, mock_async_session)
    assert e.value.status_code == 404


@pytest.mark.asyncio
async def test_export_report_bad_json(mock_async_session, sample_task, sample_report):
    _tidy_report(sample_report)
    sample_report.eu_ai_act_json = "not json"
    sample_report.vertex_event_hash = None
    with patch.object(reports_api.task_repo, "get_task", AsyncMock(return_value=sample_task)), \
         patch.object(reports_api.report_repo, "get_report_by_task_id", AsyncMock(return_value=sample_report)):
        result = await reports_api.export_report(
            sample_task.id, "eu_ai_act", False, {}, mock_async_session,
        )
    assert "article_9_risk_management" not in result
    assert "schema_version" in result


# --------------------------------------------------------------------------- #
# GET /reports/{task_id}/export?signed=true
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_export_report_signed_happy_path(
    mock_async_session, sample_task, sample_report, with_signing_key
):
    _tidy_report(sample_report)
    sample_task.vertex_finalised_at = None
    with patch.object(reports_api.task_repo, "get_task", AsyncMock(return_value=sample_task)), \
         patch.object(reports_api.report_repo, "get_report_by_task_id", AsyncMock(return_value=sample_report)):
        result = await reports_api.export_report(
            task_id=sample_task.id, format="eu_ai_act", signed=True,
            _key_meta={}, session=mock_async_session,
        )
    assert result["schema"] == export_signer.SIGNATURE_SCHEMA_VERSION
    assert "payload" in result
    assert result["signature"]["algorithm"] == "HMAC-SHA256"
    assert result["signature"]["signing_key_id"] == "api-test-key"
    assert len(result["signature"]["signature_hex"]) == 64
    # stored_signature is None because _tidy_report cleared it
    assert result["stored_signature"] is None
    # Fresh signature must verify against the payload
    assert export_signer.verify_signature(
        result["payload"],
        result["signature"]["signature_hex"],
        result["signature"]["signing_key_id"],
    ) is True


@pytest.mark.asyncio
async def test_export_report_signed_echoes_stored_signature(
    mock_async_session, sample_task, sample_report, with_signing_key
):
    _tidy_report(sample_report)
    sample_report.org_signature = "cc" * 32
    sample_report.signing_key_id = "api-test-key"
    sample_report.signed_at = MagicMock()
    sample_report.signed_at.isoformat = MagicMock(return_value="2026-04-20T00:00:00+00:00")
    sample_task.vertex_finalised_at = None
    with patch.object(reports_api.task_repo, "get_task", AsyncMock(return_value=sample_task)), \
         patch.object(reports_api.report_repo, "get_report_by_task_id", AsyncMock(return_value=sample_report)):
        result = await reports_api.export_report(
            task_id=sample_task.id, format="eu_ai_act", signed=True,
            _key_meta={}, session=mock_async_session,
        )
    assert result["stored_signature"]["signature_hex"] == "cc" * 32
    assert result["stored_signature"]["signed_at"] == "2026-04-20T00:00:00+00:00"


@pytest.mark.asyncio
async def test_export_report_signed_raises_503_when_no_key(
    mock_async_session, sample_task, sample_report, without_signing_key
):
    _tidy_report(sample_report)
    sample_task.vertex_finalised_at = None
    with patch.object(reports_api.task_repo, "get_task", AsyncMock(return_value=sample_task)), \
         patch.object(reports_api.report_repo, "get_report_by_task_id", AsyncMock(return_value=sample_report)):
        with pytest.raises(HTTPException) as e:
            await reports_api.export_report(
                sample_task.id, "eu_ai_act", True, {}, mock_async_session,
            )
    assert e.value.status_code == 503
    assert "signing unavailable" in e.value.detail.lower()


# --------------------------------------------------------------------------- #
# POST /reports/{task_id}/sign
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_sign_report_endpoint_happy_path(
    mock_async_session, sample_task, sample_report, with_signing_key
):
    _tidy_report(sample_report)
    sample_task.vertex_finalised_at = None
    sign_spy = AsyncMock(return_value=sample_report)
    with patch.object(reports_api.task_repo, "get_task", AsyncMock(return_value=sample_task)), \
         patch.object(reports_api.report_repo, "get_report_by_task_id", AsyncMock(return_value=sample_report)), \
         patch.object(reports_api.report_repo, "sign_report", sign_spy):
        result = await reports_api.sign_report_endpoint(
            task_id=sample_task.id, _key_meta={}, session=mock_async_session,
        )
    assert result["persisted"] is True
    assert result["schema"] == export_signer.SIGNATURE_SCHEMA_VERSION
    assert result["signature"]["signing_key_id"] == "api-test-key"

    # repo.sign_report must have been called with the signature from the envelope
    sign_spy.assert_awaited_once()
    call_kwargs = sign_spy.await_args.kwargs
    assert call_kwargs["signature_hex"] == result["signature"]["signature_hex"]
    assert call_kwargs["signing_key_id"] == "api-test-key"
    mock_async_session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_sign_report_endpoint_raises_503_when_no_key(
    mock_async_session, sample_task, sample_report, without_signing_key
):
    _tidy_report(sample_report)
    sample_task.vertex_finalised_at = None
    with patch.object(reports_api.task_repo, "get_task", AsyncMock(return_value=sample_task)), \
         patch.object(reports_api.report_repo, "get_report_by_task_id", AsyncMock(return_value=sample_report)):
        with pytest.raises(HTTPException) as e:
            await reports_api.sign_report_endpoint(
                task_id=sample_task.id, _key_meta={}, session=mock_async_session,
            )
    assert e.value.status_code == 503


@pytest.mark.asyncio
async def test_sign_report_endpoint_task_not_found(mock_async_session, with_signing_key):
    with patch.object(reports_api.task_repo, "get_task", AsyncMock(return_value=None)):
        with pytest.raises(HTTPException) as e:
            await reports_api.sign_report_endpoint(
                task_id=uuid.uuid4(), _key_meta={}, session=mock_async_session,
            )
    assert e.value.status_code == 404


@pytest.mark.asyncio
async def test_sign_report_endpoint_task_not_completed(
    mock_async_session, sample_task, with_signing_key
):
    sample_task.status = "REVIEWING"
    with patch.object(reports_api.task_repo, "get_task", AsyncMock(return_value=sample_task)):
        with pytest.raises(HTTPException) as e:
            await reports_api.sign_report_endpoint(
                task_id=sample_task.id, _key_meta={}, session=mock_async_session,
            )
    assert e.value.status_code == 400


@pytest.mark.asyncio
async def test_sign_report_endpoint_missing_report(
    mock_async_session, sample_task, with_signing_key
):
    with patch.object(reports_api.task_repo, "get_task", AsyncMock(return_value=sample_task)), \
         patch.object(reports_api.report_repo, "get_report_by_task_id", AsyncMock(return_value=None)):
        with pytest.raises(HTTPException) as e:
            await reports_api.sign_report_endpoint(
                task_id=sample_task.id, _key_meta={}, session=mock_async_session,
            )
    assert e.value.status_code == 404
