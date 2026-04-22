"""Auditex -- Webhooks CRUD + trigger API (Phase 11 Item 6)."""
from __future__ import annotations

import secrets
import uuid

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, HttpUrl

from app.api.middleware.auth import require_api_key
from db.connection import get_db_session
from db.repositories import webhook_repo
from services import notification_service

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


class SubscriptionIn(BaseModel):
    url: HttpUrl
    event_types: list[str] = Field(default_factory=list)
    description: str | None = None
    secret_hex: str | None = None


def _sub_to_dict(sub) -> dict:
    return {
        "id": str(sub.id),
        "url": sub.url,
        "event_types": sub.event_types,
        "active": sub.active,
        "description": sub.description,
        "secret_hex": sub.secret_hex,
        "created_at": sub.created_at.isoformat() if sub.created_at else None,
    }


def _delivery_to_dict(d) -> dict:
    return {
        "id": str(d.id),
        "subscription_id": str(d.subscription_id),
        "event_type": d.event_type,
        "status": d.status,
        "response_status": d.response_status,
        "attempt_count": d.attempt_count,
        "delivered_at": d.delivered_at.isoformat() if d.delivered_at else None,
        "created_at": d.created_at.isoformat() if d.created_at else None,
    }


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_webhook(
    body: SubscriptionIn,
    _key_meta: dict = Depends(require_api_key),
    session=Depends(get_db_session),
):
    secret = body.secret_hex or secrets.token_hex(32)
    # Pydantic HttpUrl -> str
    url_str = str(body.url)
    sub = await webhook_repo.create_subscription(
        session, url=url_str, secret_hex=secret,
        event_types=body.event_types, description=body.description,
    )
    await session.commit()
    return _sub_to_dict(sub)


@router.get("/", response_model=dict)
async def list_webhooks(
    active_only: bool = Query(default=False),
    limit: int = Query(default=100, ge=1, le=500),
    _key_meta: dict = Depends(require_api_key),
    session=Depends(get_db_session),
):
    subs = await webhook_repo.list_subscriptions(session, active_only=active_only, limit=limit)
    return {"count": len(subs), "subscriptions": [_sub_to_dict(s) for s in subs]}


@router.get("/{sub_id}", response_model=dict)
async def get_webhook(
    sub_id: uuid.UUID,
    _key_meta: dict = Depends(require_api_key),
    session=Depends(get_db_session),
):
    sub = await webhook_repo.get_subscription(session, sub_id)
    if sub is None:
        raise HTTPException(status_code=404, detail=f"Subscription {sub_id} not found.")
    return _sub_to_dict(sub)


@router.delete("/{sub_id}", response_model=dict)
async def deactivate_webhook(
    sub_id: uuid.UUID,
    _key_meta: dict = Depends(require_api_key),
    session=Depends(get_db_session),
):
    sub = await webhook_repo.deactivate_subscription(session, sub_id)
    if sub is None:
        raise HTTPException(status_code=404, detail=f"Subscription {sub_id} not found.")
    await session.commit()
    return _sub_to_dict(sub)


class DeliverRequest(BaseModel):
    event_type: str
    payload: dict


@router.post("/{sub_id}/deliver", response_model=dict)
async def deliver_to_webhook(
    sub_id: uuid.UUID,
    body: DeliverRequest = Body(...),
    _key_meta: dict = Depends(require_api_key),
    session=Depends(get_db_session),
):
    """Synchronously deliver a payload to one subscription and record the result."""
    sub = await webhook_repo.get_subscription(session, sub_id)
    if sub is None:
        raise HTTPException(status_code=404, detail=f"Subscription {sub_id} not found.")
    if not sub.active:
        raise HTTPException(status_code=400, detail="Subscription is not active.")
    status_str, resp_status, resp_body, sig_hex = await notification_service.deliver(
        url=sub.url, event_type=body.event_type, payload=body.payload, secret_hex=sub.secret_hex,
    )
    delivery = await webhook_repo.create_delivery(
        session, subscription_id=sub.id, event_type=body.event_type,
        payload=body.payload, signature_hex=sig_hex,
    )
    delivery = await webhook_repo.mark_delivery_result(
        session, delivery.id, status=status_str,
        response_status=resp_status, response_body=resp_body,
    )
    await session.commit()
    return _delivery_to_dict(delivery)


@router.get("/{sub_id}/deliveries", response_model=dict)
async def list_deliveries(
    sub_id: uuid.UUID,
    limit: int = Query(default=100, ge=1, le=500),
    _key_meta: dict = Depends(require_api_key),
    session=Depends(get_db_session),
):
    sub = await webhook_repo.get_subscription(session, sub_id)
    if sub is None:
        raise HTTPException(status_code=404, detail=f"Subscription {sub_id} not found.")
    deliveries = await webhook_repo.list_deliveries_for_subscription(session, sub_id, limit=limit)
    return {"count": len(deliveries), "deliveries": [_delivery_to_dict(d) for d in deliveries]}
