"""
Auditex -- FoxMQ client (STUB -- Phase 5).

STUB MODE: FoxMQ/Vertex infrastructure is not yet deployed.
This stub logs and returns True without performing any real MQTT publish.

When real FoxMQ is available (Phase 6+), replace ONLY this file:
  - Import the real MQTT client (e.g. paho-mqtt or aiomqtt)
  - Connect to FOXMQ_BROKER_URL from settings
  - Publish event_payload as JSON to the canonical topic
  - Return True on success, raise on failure
  - The stub interface (publish_event signature) stays identical

DESIGN CONTRACT:
  publish_event(event_payload: dict) -> bool
    True  = event accepted by broker (or stub logged it)
    False / raises = delivery failure (caller should handle)
"""
from __future__ import annotations

import json
import logging

logger = logging.getLogger(__name__)

# Stub flag -- will be False when real FoxMQ client is wired up
_STUB_MODE = True


def publish_event(event_payload: dict) -> bool:
    """
    Publish a task event to the FoxMQ broker.

    STUB: Logs the event and returns True immediately.
    Real implementation: MQTT publish to FoxMQ broker topic.

    Args:
        event_payload: The canonical event dict from event_builder.

    Returns:
        True if event was accepted (or stub).

    Raises:
        FoxMQPublishError: If real broker publish fails (not raised in stub).
    """
    if _STUB_MODE:
        event_type = event_payload.get("event_type", "unknown")
        task_id = event_payload.get("task_id", "unknown")
        logger.info(
            "FOXMQ_STUB: event published | event_type=%s task_id=%s",
            event_type, task_id,
        )
        return True

    # --- Real implementation placeholder (Phase 6+) ---
    # from app.config import settings
    # import aiomqtt
    # topic = f"auditex/events/{event_payload['event_type']}"
    # payload_bytes = json.dumps(event_payload, sort_keys=True).encode("utf-8")
    # async with aiomqtt.Client(settings.FOXMQ_BROKER_URL) as client:
    #     await client.publish(topic, payload=payload_bytes, qos=1)
    # return True

    raise NotImplementedError("Real FoxMQ client not yet implemented (Phase 6+)")


class FoxMQPublishError(Exception):
    """Raised when FoxMQ publish fails in real mode."""
