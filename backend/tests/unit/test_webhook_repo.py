"""Tests for db.repositories.webhook_repo."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from db.repositories import webhook_repo


@pytest.fixture
def fake_sub():
    s = MagicMock()
    s.id = uuid.uuid4()
    s.url = "https://e.com"
    s.secret_hex = "ab" * 32
    s.active = True
    s.event_types = ["x"]
    s.description = None
    s.created_at = datetime(2026, 4, 22, tzinfo=timezone.utc)
    return s


@pytest.fixture
def fake_delivery():
    d = MagicMock()
    d.id = uuid.uuid4()
    d.subscription_id = uuid.uuid4()
    d.event_type = "e1"
    d.status = "PENDING"
    d.response_status = None
    d.response_body = None
    d.attempt_count = 0
    d.delivered_at = None
    d.created_at = datetime(2026, 4, 22, tzinfo=timezone.utc)
    return d


@pytest.mark.asyncio
async def test_create_subscription_defaults(mock_async_session):
    sub = await webhook_repo.create_subscription(
        mock_async_session, url="https://x", secret_hex="ff" * 32,
    )
    assert sub.url == "https://x"
    assert sub.event_types == []
    assert sub.description is None
    assert sub.active is True
    mock_async_session.add.assert_called_once()


@pytest.mark.asyncio
async def test_create_subscription_with_event_types(mock_async_session):
    sub = await webhook_repo.create_subscription(
        mock_async_session, url="https://x", secret_hex="aa" * 32,
        event_types=["task.completed", "task.failed"], description="d",
    )
    assert sub.event_types == ["task.completed", "task.failed"]
    assert sub.description == "d"


@pytest.mark.asyncio
async def test_get_subscription_found(mock_async_session, fake_sub):
    mock_async_session._result.scalar_one_or_none.return_value = fake_sub
    r = await webhook_repo.get_subscription(mock_async_session, fake_sub.id)
    assert r is fake_sub


@pytest.mark.asyncio
async def test_get_subscription_not_found(mock_async_session):
    mock_async_session._result.scalar_one_or_none.return_value = None
    r = await webhook_repo.get_subscription(mock_async_session, uuid.uuid4())
    assert r is None


@pytest.mark.asyncio
async def test_list_subscriptions_no_filter(mock_async_session, fake_sub):
    mock_async_session._result.scalars.return_value.all.return_value = [fake_sub]
    r = await webhook_repo.list_subscriptions(mock_async_session)
    assert list(r) == [fake_sub]


@pytest.mark.asyncio
async def test_list_subscriptions_active_only(mock_async_session, fake_sub):
    mock_async_session._result.scalars.return_value.all.return_value = [fake_sub]
    r = await webhook_repo.list_subscriptions(mock_async_session, active_only=True, limit=5)
    assert list(r) == [fake_sub]


@pytest.mark.asyncio
async def test_deactivate_subscription_happy_path(mock_async_session, fake_sub):
    mock_async_session._result.scalar_one_or_none.return_value = fake_sub
    r = await webhook_repo.deactivate_subscription(mock_async_session, fake_sub.id)
    assert r is fake_sub
    assert fake_sub.active is False


@pytest.mark.asyncio
async def test_deactivate_subscription_not_found(mock_async_session):
    mock_async_session._result.scalar_one_or_none.return_value = None
    r = await webhook_repo.deactivate_subscription(mock_async_session, uuid.uuid4())
    assert r is None


@pytest.mark.asyncio
async def test_create_delivery(mock_async_session):
    sid = uuid.uuid4()
    d = await webhook_repo.create_delivery(
        mock_async_session, subscription_id=sid, event_type="e",
        payload={"a": 1}, signature_hex="dd" * 32,
    )
    assert d.subscription_id == sid
    assert d.event_type == "e"
    assert d.status == "PENDING"
    assert d.attempt_count == 0
    mock_async_session.add.assert_called_once()


@pytest.mark.asyncio
async def test_mark_delivery_result_delivered(mock_async_session, fake_delivery):
    fake_delivery.attempt_count = 1
    mock_async_session._result.scalar_one_or_none.return_value = fake_delivery
    r = await webhook_repo.mark_delivery_result(
        mock_async_session, fake_delivery.id, status="DELIVERED", response_status=200, response_body="ok",
    )
    assert r is fake_delivery
    assert fake_delivery.status == "DELIVERED"
    assert fake_delivery.response_status == 200
    assert fake_delivery.attempt_count == 2
    assert isinstance(fake_delivery.delivered_at, datetime)


@pytest.mark.asyncio
async def test_mark_delivery_result_failed_no_delivered_at(mock_async_session, fake_delivery):
    fake_delivery.attempt_count = 0
    fake_delivery.delivered_at = None
    mock_async_session._result.scalar_one_or_none.return_value = fake_delivery
    r = await webhook_repo.mark_delivery_result(
        mock_async_session, fake_delivery.id, status="FAILED", response_status=500,
    )
    assert r.status == "FAILED"
    assert fake_delivery.delivered_at is None


@pytest.mark.asyncio
async def test_mark_delivery_result_not_found(mock_async_session):
    mock_async_session._result.scalar_one_or_none.return_value = None
    r = await webhook_repo.mark_delivery_result(
        mock_async_session, uuid.uuid4(), status="FAILED",
    )
    assert r is None


@pytest.mark.asyncio
async def test_list_deliveries_for_subscription(mock_async_session, fake_delivery):
    mock_async_session._result.scalars.return_value.all.return_value = [fake_delivery]
    r = await webhook_repo.list_deliveries_for_subscription(mock_async_session, fake_delivery.subscription_id)
    assert list(r) == [fake_delivery]
