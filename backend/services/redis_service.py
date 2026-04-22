"""Auditex -- Redis service wrapper (Phase 11 Item 7).

Typed facade over redis.asyncio that:
  - centralises connection lifecycle (from_url, close)
  - exposes only the subset of commands Auditex actually uses
  - makes swapping Redis for a mock trivial in tests
  - fails closed with a clear RedisServiceError on transport failures
"""
from __future__ import annotations

import json
import logging
from typing import Any

import redis.asyncio as aioredis

from app.config import settings

logger = logging.getLogger(__name__)


class RedisServiceError(Exception):
    """Raised when a Redis operation fails at transport level."""


class RedisService:
    """Async typed wrapper over redis.asyncio.Redis."""

    def __init__(self, url: str | None = None):
        self._url = url or settings.REDIS_URL
        self._client: aioredis.Redis | None = None

    async def _get_client(self) -> aioredis.Redis:
        if self._client is None:
            self._client = aioredis.from_url(self._url, decode_responses=True)
        return self._client

    async def close(self) -> None:
        """Close the underlying connection pool."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def set_json(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        """Set key to JSON-serialised value. Optional TTL in seconds."""
        try:
            payload = json.dumps(value, sort_keys=True)
            client = await self._get_client()
            if ttl_seconds is not None:
                await client.set(key, payload, ex=ttl_seconds)
            else:
                await client.set(key, payload)
        except Exception as exc:
            raise RedisServiceError(f"set_json failed for key={key}: {exc}") from exc

    async def get_json(self, key: str) -> Any:
        """Fetch key and JSON-deserialise. Returns None if key missing."""
        try:
            client = await self._get_client()
            raw = await client.get(key)
            if raw is None:
                return None
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RedisServiceError(f"get_json bad JSON at key={key}: {exc}") from exc
        except Exception as exc:
            raise RedisServiceError(f"get_json failed for key={key}: {exc}") from exc

    async def delete(self, key: str) -> int:
        """DEL key. Returns number of keys removed (0 or 1)."""
        try:
            client = await self._get_client()
            return await client.delete(key)
        except Exception as exc:
            raise RedisServiceError(f"delete failed for key={key}: {exc}") from exc

    async def exists(self, key: str) -> bool:
        """True if key exists, False otherwise."""
        try:
            client = await self._get_client()
            return bool(await client.exists(key))
        except Exception as exc:
            raise RedisServiceError(f"exists failed for key={key}: {exc}") from exc

    async def incr(self, key: str, amount: int = 1) -> int:
        """Atomically increment key by amount. Returns new value."""
        try:
            client = await self._get_client()
            return await client.incrby(key, amount)
        except Exception as exc:
            raise RedisServiceError(f"incr failed for key={key}: {exc}") from exc

    async def expire(self, key: str, ttl_seconds: int) -> bool:
        """Set TTL on an existing key. True if set, False if key missing."""
        try:
            client = await self._get_client()
            return bool(await client.expire(key, ttl_seconds))
        except Exception as exc:
            raise RedisServiceError(f"expire failed for key={key}: {exc}") from exc


# Singleton instance for convenience. Use get_redis_service() in app code.
_default_service: RedisService | None = None


def get_redis_service() -> RedisService:
    """Return a lazily-constructed default RedisService."""
    global _default_service
    if _default_service is None:
        _default_service = RedisService()
    return _default_service


def reset_default_service() -> None:
    """Tests use this to drop the module-level singleton."""
    global _default_service
    _default_service = None
