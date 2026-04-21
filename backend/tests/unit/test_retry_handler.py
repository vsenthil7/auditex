"""Tests for core.execution.retry_handler."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from core.execution.retry_handler import (
    _BACKOFF_SCHEDULE,
    exponential_backoff,
    route_to_dlq,
)


@pytest.mark.asyncio
async def test_exponential_backoff_attempt_1():
    with patch("asyncio.sleep", AsyncMock()) as mock_sleep:
        await exponential_backoff(1)
    mock_sleep.assert_awaited_once_with(_BACKOFF_SCHEDULE[0])


@pytest.mark.asyncio
async def test_exponential_backoff_attempt_2():
    with patch("asyncio.sleep", AsyncMock()) as mock_sleep:
        await exponential_backoff(2)
    mock_sleep.assert_awaited_once_with(_BACKOFF_SCHEDULE[1])


@pytest.mark.asyncio
async def test_exponential_backoff_clamps_to_last_entry():
    with patch("asyncio.sleep", AsyncMock()) as mock_sleep:
        await exponential_backoff(99)
    mock_sleep.assert_awaited_once_with(_BACKOFF_SCHEDULE[-1])


@pytest.mark.asyncio
async def test_route_to_dlq_calls_repos(mock_async_session):
    tid = uuid.uuid4()
    with patch(
        "core.execution.retry_handler.task_repo.update_task_status", AsyncMock()
    ) as m_update, patch(
        "core.execution.retry_handler.event_repo.insert_event", AsyncMock()
    ) as m_insert:
        await route_to_dlq(mock_async_session, tid, "test reason")
    m_update.assert_awaited_once()
    m_insert.assert_awaited_once()
    # Check the reason was truncated to 500
    call_args = m_update.await_args
    assert call_args.kwargs["status"] == "FAILED"


@pytest.mark.asyncio
async def test_route_to_dlq_truncates_long_reason(mock_async_session):
    tid = uuid.uuid4()
    long_reason = "x" * 1000
    with patch(
        "core.execution.retry_handler.task_repo.update_task_status", AsyncMock()
    ) as m_update, patch(
        "core.execution.retry_handler.event_repo.insert_event", AsyncMock()
    ):
        await route_to_dlq(mock_async_session, tid, long_reason)
    assert len(m_update.await_args.kwargs["failure_reason"]) == 500
