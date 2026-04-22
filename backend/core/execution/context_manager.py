"""Auditex -- Redis-backed multi-step task context (Phase 11 Item 8).

Long-running agent tasks need to persist intermediate state between steps
(executor output, reviewer notes, retry counters, draft narrative). This
module provides an async key-value context keyed by task_id, stored in
Redis with a configurable TTL so orphaned contexts age out.

Namespace layout:
  ctx:{task_id}              -> JSON dict of all values for this task
  ctx:{task_id}:history      -> JSON list of (step, timestamp, note)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from services.redis_service import RedisService

DEFAULT_TTL_SECONDS = 24 * 60 * 60  # 24h
KEY_PREFIX = "ctx:"
HISTORY_SUFFIX = ":history"


class ContextNotFoundError(Exception):
    """Raised when the caller asks for a context that was never created."""


def _ctx_key(task_id: uuid.UUID | str) -> str:
    return f"{KEY_PREFIX}{task_id}"


def _history_key(task_id: uuid.UUID | str) -> str:
    return _ctx_key(task_id) + HISTORY_SUFFIX


class ContextManager:
    """Per-task context store backed by Redis."""

    def __init__(self, redis: RedisService, ttl_seconds: int = DEFAULT_TTL_SECONDS):
        self._redis = redis
        self._ttl = ttl_seconds

    async def create(self, task_id: uuid.UUID | str, initial: dict | None = None) -> dict:
        """Create a new context. Returns the stored dict. Idempotent re-create overwrites."""
        ctx = dict(initial or {})
        ctx["__created_at__"] = datetime.now(timezone.utc).isoformat()
        await self._redis.set_json(_ctx_key(task_id), ctx, ttl_seconds=self._ttl)
        await self._redis.set_json(_history_key(task_id), [], ttl_seconds=self._ttl)
        return ctx

    async def get(self, task_id: uuid.UUID | str) -> dict:
        """Return the stored context. Raises ContextNotFoundError if absent."""
        stored = await self._redis.get_json(_ctx_key(task_id))
        if stored is None:
            raise ContextNotFoundError(f"No context for task {task_id}")
        return stored

    async def update(self, task_id: uuid.UUID | str, patch: dict) -> dict:
        """Merge patch into the stored dict (shallow). Returns the merged result."""
        ctx = await self.get(task_id)
        ctx.update(patch)
        await self._redis.set_json(_ctx_key(task_id), ctx, ttl_seconds=self._ttl)
        return ctx

    async def append_history(self, task_id: uuid.UUID | str, step: str, note: str | None = None) -> list:
        """Append a {step, timestamp, note} record. Returns the updated history list."""
        history = await self._redis.get_json(_history_key(task_id)) or []
        entry = {
            "step": step,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "note": note,
        }
        history.append(entry)
        await self._redis.set_json(_history_key(task_id), history, ttl_seconds=self._ttl)
        return history

    async def get_history(self, task_id: uuid.UUID | str) -> list:
        """Fetch the history list. Returns [] if no history recorded."""
        history = await self._redis.get_json(_history_key(task_id))
        return history or []

    async def delete(self, task_id: uuid.UUID | str) -> None:
        """Remove both the context and history keys. No error if absent."""
        await self._redis.delete(_ctx_key(task_id))
        await self._redis.delete(_history_key(task_id))

    async def exists(self, task_id: uuid.UUID | str) -> bool:
        """True if a context has been created for this task."""
        return await self._redis.exists(_ctx_key(task_id))
