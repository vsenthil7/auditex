"""Tests for app.api.v1.webhooks route handlers."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from pydantic import HttpUrl

from app.api.v1 import webhooks as wh_api
from app.api.v1.webhooks import SubscriptionIn, DeliverRequest


@pytest.fixture
def fake_sub():
    s = MagicMock()
    s.id = uuid.uuid4()
    s.url = "https://e.com/"
    s.secret_hex = "ab" * 32
    s.event_types = ["task.completed"]
    s.active = True
    s.description = "d"
    s.created_at = datetime(2026, 4, 22, tzinfo=timezone.utc)
    return s


@pytest.fixture
def fake_delivery():
    d = MagicMock()
    d.id = uuid.uuid4()
    d.subscription_id = uuid.uuid4()
    d.event_type = "task.completed"
    d.status = "DELIVERED"
    d.response_status = 200
    d.attempt_count = 1
    d.delivered_at = datetime(2026, 4, 22, 1, tzinfo=timezone.utc)
    d.created_at = datetime(2026, 4, 22, tzinfo=timezone.utc)
    return d


def test_sub_to_dict(fake_sub):
    d = wh_api._sub_to_dict(fake_sub)
    assert d["id"] == str(fake_sub.id)
    assert d["url"] == fake_sub.url
    assert d["active"] is True
    assert d["created_at"] == "2026-04-22T00:00:00+00:00"


def test_sub_to_dict_handles_missing_created_at():
    s = MagicMock()
    s.id = uuid.uuid4(); s.url = "u"; s.event_types = []; s.active = True
    s.description = None; s.secret_hex = "aa" * 32; s.created_at = None
    d = wh_api._sub_to_dict(s)
    assert d["created_at"] is None


def test_delivery_to_dict(fake_delivery):
    d = wh_api._delivery_to_dict(fake_delivery)
    assert d["status"] == "DELIVERED"
    assert d["response_status"] == 200
    assert d["attempt_count"] == 1
    assert d["delivered_at"] == "2026-04-22T01:00:00+00:00"


def test_delivery_to_dict_handles_none_delivered_at():
    d = MagicMock()
    d.id = uuid.uuid4(); d.subscription_id = uuid.uuid4()
    d.event_type = "e"; d.status = "PENDING"
    d.response_status = None; d.attempt_count = 0
    d.delivered_at = None; d.created_at = None
    out = wh_api._delivery_to_dict(d)
    assert out["delivered_at"] is None
    assert out["created_at"] is None


@pytest.mark.asyncio
async def test_create_webhook_with_provided_secret(mock_async_session, fake_sub):
    body = SubscriptionIn(url="https://e.com", event_types=["x"], description="d", secret_hex="cc" * 32)
    spy = AsyncMock(return_value=fake_sub)
    with patch.object(wh_api.webhook_repo, "create_subscription", spy):
        r = await wh_api.create_webhook(body, {}, mock_async_session)
    assert r["id"] == str(fake_sub.id)
    assert spy.await_args.kwargs["secret_hex"] == "cc" * 32
    mock_async_session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_create_webhook_auto_generates_secret(mock_async_session, fake_sub):
    body = SubscriptionIn(url="https://e.com", event_types=[], description=None, secret_hex=None)
    spy = AsyncMock(return_value=fake_sub)
    with patch.object(wh_api.webhook_repo, "create_subscription", spy):
        await wh_api.create_webhook(body, {}, mock_async_session)
    # Auto-generated secret should be 64-char hex
    assert len(spy.await_args.kwargs["secret_hex"]) == 64


@pytest.mark.asyncio
async def test_list_webhooks_defaults(mock_async_session, fake_sub):
    with patch.object(wh_api.webhook_repo, "list_subscriptions", AsyncMock(return_value=[fake_sub])):
        r = await wh_api.list_webhooks(False, 100, {}, mock_async_session)
    assert r["count"] == 1
    assert len(r["subscriptions"]) == 1


@pytest.mark.asyncio
async def test_list_webhooks_active_only(mock_async_session, fake_sub):
    spy = AsyncMock(return_value=[fake_sub])
    with patch.object(wh_api.webhook_repo, "list_subscriptions", spy):
        await wh_api.list_webhooks(True, 5, {}, mock_async_session)
    assert spy.await_args.kwargs["active_only"] is True
    assert spy.await_args.kwargs["limit"] == 5


@pytest.mark.asyncio
async def test_get_webhook_happy_path(mock_async_session, fake_sub):
    with patch.object(wh_api.webhook_repo, "get_subscription", AsyncMock(return_value=fake_sub)):
        r = await wh_api.get_webhook(fake_sub.id, {}, mock_async_session)
    assert r["id"] == str(fake_sub.id)


@pytest.mark.asyncio
async def test_get_webhook_404(mock_async_session):
    with patch.object(wh_api.webhook_repo, "get_subscription", AsyncMock(return_value=None)):
        with pytest.raises(HTTPException) as e:
            await wh_api.get_webhook(uuid.uuid4(), {}, mock_async_session)
    assert e.value.status_code == 404


@pytest.mark.asyncio
async def test_deactivate_webhook_happy_path(mock_async_session, fake_sub):
    fake_sub.active = False
    with patch.object(wh_api.webhook_repo, "deactivate_subscription", AsyncMock(return_value=fake_sub)):
        r = await wh_api.deactivate_webhook(fake_sub.id, {}, mock_async_session)
    assert r["active"] is False
    mock_async_session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_deactivate_webhook_404(mock_async_session):
    with patch.object(wh_api.webhook_repo, "deactivate_subscription", AsyncMock(return_value=None)):
        with pytest.raises(HTTPException) as e:
            await wh_api.deactivate_webhook(uuid.uuid4(), {}, mock_async_session)
    assert e.value.status_code == 404


@pytest.mark.asyncio
async def test_deliver_to_webhook_happy_path(mock_async_session, fake_sub, fake_delivery):
    body = DeliverRequest(event_type="task.completed", payload={"a": 1})
    p1 = patch.object(wh_api.webhook_repo, "get_subscription", AsyncMock(return_value=fake_sub))
    p2 = patch.object(wh_api.notification_service, "deliver", AsyncMock(return_value=("DELIVERED", 200, "ok", "ab" * 32)))
    p3 = patch.object(wh_api.webhook_repo, "create_delivery", AsyncMock(return_value=fake_delivery))
    p4 = patch.object(wh_api.webhook_repo, "mark_delivery_result", AsyncMock(return_value=fake_delivery))
    with p1, p2, p3, p4:
        r = await wh_api.deliver_to_webhook(fake_sub.id, body, {}, mock_async_session)
    assert r["status"] == "DELIVERED"
    mock_async_session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_deliver_to_webhook_404(mock_async_session):
    body = DeliverRequest(event_type="e", payload={})
    with patch.object(wh_api.webhook_repo, "get_subscription", AsyncMock(return_value=None)):
        with pytest.raises(HTTPException) as e:
            await wh_api.deliver_to_webhook(uuid.uuid4(), body, {}, mock_async_session)
    assert e.value.status_code == 404


@pytest.mark.asyncio
async def test_deliver_to_webhook_inactive_rejected(mock_async_session, fake_sub):
    fake_sub.active = False
    body = DeliverRequest(event_type="e", payload={})
    with patch.object(wh_api.webhook_repo, "get_subscription", AsyncMock(return_value=fake_sub)):
        with pytest.raises(HTTPException) as e:
            await wh_api.deliver_to_webhook(fake_sub.id, body, {}, mock_async_session)
    assert e.value.status_code == 400


@pytest.mark.asyncio
async def test_list_deliveries_happy_path(mock_async_session, fake_sub, fake_delivery):
    p1 = patch.object(wh_api.webhook_repo, "get_subscription", AsyncMock(return_value=fake_sub))
    p2 = patch.object(wh_api.webhook_repo, "list_deliveries_for_subscription", AsyncMock(return_value=[fake_delivery]))
    with p1, p2:
        r = await wh_api.list_deliveries(fake_sub.id, 100, {}, mock_async_session)
    assert r["count"] == 1


@pytest.mark.asyncio
async def test_list_deliveries_sub_not_found(mock_async_session):
    with patch.object(wh_api.webhook_repo, "get_subscription", AsyncMock(return_value=None)):
        with pytest.raises(HTTPException) as e:
            await wh_api.list_deliveries(uuid.uuid4(), 100, {}, mock_async_session)
    assert e.value.status_code == 404
