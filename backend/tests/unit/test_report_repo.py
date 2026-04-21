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


# --------------------------------------------------------------------------- #
# sign_report (Phase 11 Item 1b.1)
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_sign_report_persists_signature(mock_async_session, sample_report):
    mock_async_session._result.scalar_one_or_none.return_value = sample_report
    task_id = sample_report.task_id
    sig_hex = "ab" * 32

    result = await report_repo.sign_report(
        mock_async_session,
        task_id,
        signature_hex=sig_hex,
        signing_key_id="k-new",
    )

    assert result is sample_report
    assert sample_report.org_signature == sig_hex
    assert sample_report.signing_key_id == "k-new"
    # Default signed_at should be a timezone-aware datetime ~now
    assert isinstance(sample_report.signed_at, datetime)
    assert sample_report.signed_at.tzinfo is not None
    mock_async_session.flush.assert_awaited()
    mock_async_session.refresh.assert_awaited_with(sample_report)


@pytest.mark.asyncio
async def test_sign_report_respects_explicit_signed_at(mock_async_session, sample_report):
    mock_async_session._result.scalar_one_or_none.return_value = sample_report
    fixed = datetime(2026, 4, 21, 22, 33, tzinfo=timezone.utc)

    await report_repo.sign_report(
        mock_async_session,
        sample_report.task_id,
        signature_hex="cd" * 32,
        signing_key_id="k-old",
        signed_at=fixed,
    )

    assert sample_report.signed_at == fixed
    assert sample_report.signing_key_id == "k-old"


@pytest.mark.asyncio
async def test_sign_report_returns_none_if_report_missing(mock_async_session):
    mock_async_session._result.scalar_one_or_none.return_value = None

    result = await report_repo.sign_report(
        mock_async_session,
        uuid.uuid4(),
        signature_hex="aa" * 32,
        signing_key_id="k-new",
    )

    assert result is None
    # No flush/refresh because there was nothing to update
    mock_async_session.flush.assert_not_awaited()
    mock_async_session.refresh.assert_not_awaited()


@pytest.mark.asyncio
async def test_sign_report_is_idempotent_overwrite(mock_async_session, sample_report):
    """Re-signing replaces the previous signature (last-write-wins)."""
    sample_report.org_signature = "old" * 21 + "x"
    sample_report.signing_key_id = "k-ancient"
    mock_async_session._result.scalar_one_or_none.return_value = sample_report

    await report_repo.sign_report(
        mock_async_session,
        sample_report.task_id,
        signature_hex="ff" * 32,
        signing_key_id="k-current",
    )

    assert sample_report.org_signature == "ff" * 32
    assert sample_report.signing_key_id == "k-current"
