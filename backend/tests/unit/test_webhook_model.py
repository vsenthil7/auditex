"""Tests for db.models.webhook."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from db.models.webhook import WebhookSubscription, WebhookDelivery


def test_webhook_subscription_tablename():
    assert WebhookSubscription.__tablename__ == "webhook_subscriptions"


def test_webhook_delivery_tablename():
    assert WebhookDelivery.__tablename__ == "webhook_deliveries"


def test_webhook_subscription_construction():
    sid = uuid.uuid4()
    now = datetime.now(timezone.utc)
    s = WebhookSubscription(
        id=sid, created_at=now, url="https://example.com/h",
        secret_hex="ab" * 32, event_types=["task.completed"],
        active=True, description="test",
    )
    assert s.id == sid
    assert s.url == "https://example.com/h"
    assert s.event_types == ["task.completed"]


def test_webhook_subscription_repr():
    s = WebhookSubscription(
        id=uuid.uuid4(), created_at=datetime.now(timezone.utc),
        url="https://x.y", secret_hex="0" * 64,
        event_types=[], active=True, description=None,
    )
    r = repr(s)
    assert "WebhookSubscription" in r
    assert "https://x.y" in r


def test_webhook_delivery_construction_and_repr():
    sid = uuid.uuid4(); did = uuid.uuid4()
    d = WebhookDelivery(
        id=did, created_at=datetime.now(timezone.utc),
        subscription_id=sid, event_type="task.completed",
        payload={"a": 1}, signature_hex="ff" * 32,
        status="PENDING", response_status=None,
        response_body=None, attempt_count=0, delivered_at=None,
    )
    assert d.id == did
    assert d.subscription_id == sid
    assert d.status == "PENDING"
    r = repr(d)
    assert "WebhookDelivery" in r
    assert "PENDING" in r
