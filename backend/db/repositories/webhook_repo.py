"""Auditex -- Webhook repository (Phase 11 Item 6)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.webhook import WebhookSubscription, WebhookDelivery


async def create_subscription(
    session: AsyncSession, *, url: str, secret_hex: str,
    event_types: list | None = None, description: str | None = None,
) -> WebhookSubscription:
    sub = WebhookSubscription(
        url=url, secret_hex=secret_hex,
        event_types=event_types or [], description=description, active=True,
    )
    session.add(sub)
    await session.flush()
    await session.refresh(sub)
    return sub


async def get_subscription(session: AsyncSession, sub_id: uuid.UUID) -> WebhookSubscription | None:
    r = await session.execute(select(WebhookSubscription).where(WebhookSubscription.id == sub_id))
    return r.scalar_one_or_none()


async def list_subscriptions(
    session: AsyncSession, *, active_only: bool = False, limit: int = 100,
) -> Sequence[WebhookSubscription]:
    stmt = select(WebhookSubscription).order_by(WebhookSubscription.created_at.desc())
    if active_only:
        stmt = stmt.where(WebhookSubscription.active.is_(True))
    stmt = stmt.limit(limit)
    r = await session.execute(stmt)
    return r.scalars().all()


async def deactivate_subscription(session: AsyncSession, sub_id: uuid.UUID) -> WebhookSubscription | None:
    sub = await get_subscription(session, sub_id)
    if sub is None:
        return None
    sub.active = False
    await session.flush()
    await session.refresh(sub)
    return sub


async def create_delivery(
    session: AsyncSession, *, subscription_id: uuid.UUID,
    event_type: str, payload: dict, signature_hex: str,
) -> WebhookDelivery:
    d = WebhookDelivery(
        subscription_id=subscription_id, event_type=event_type,
        payload=payload, signature_hex=signature_hex,
        status="PENDING", attempt_count=0,
    )
    session.add(d)
    await session.flush()
    await session.refresh(d)
    return d


async def mark_delivery_result(
    session: AsyncSession, delivery_id: uuid.UUID, *,
    status: str, response_status: int | None = None,
    response_body: str | None = None,
) -> WebhookDelivery | None:
    r = await session.execute(select(WebhookDelivery).where(WebhookDelivery.id == delivery_id))
    d = r.scalar_one_or_none()
    if d is None:
        return None
    d.status = status
    d.response_status = response_status
    d.response_body = response_body
    d.attempt_count = d.attempt_count + 1
    if status == "DELIVERED":
        d.delivered_at = datetime.now(timezone.utc)
    await session.flush()
    await session.refresh(d)
    return d


async def list_deliveries_for_subscription(
    session: AsyncSession, subscription_id: uuid.UUID, *, limit: int = 100,
) -> Sequence[WebhookDelivery]:
    stmt = (
        select(WebhookDelivery)
        .where(WebhookDelivery.subscription_id == subscription_id)
        .order_by(WebhookDelivery.created_at.desc())
        .limit(limit)
    )
    r = await session.execute(stmt)
    return r.scalars().all()
