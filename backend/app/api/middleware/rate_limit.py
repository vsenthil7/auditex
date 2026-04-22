"""Auditex -- Redis-backed rate-limit middleware (Phase 11 Item 4).

Sliding-window algorithm using Redis sorted sets. Each request is scored by
wall-clock ms and added to a per-identity sorted set. On each call:
  1. Purge entries older than the window.
  2. Count remaining entries in the window.
  3. If count >= limit, reject with 429 + Retry-After.
  4. Otherwise add the new entry and set TTL on the key.

Identity = X-API-Key value if present, else client ip. Configurable via
settings.RATE_LIMIT_PER_MINUTE. Set to 0 to disable globally.
"""
from __future__ import annotations

import logging
import time

import redis.asyncio as aioredis
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings

logger = logging.getLogger(__name__)

WINDOW_SECONDS = 60
REDIS_KEY_PREFIX = "ratelimit:"


def _identity(request: Request) -> str:
    """API key takes precedence, fall back to client ip."""
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return f"k:{api_key}"
    if request.client is not None:
        return f"ip:{request.client.host}"
    return "ip:unknown"


async def check_rate_limit(redis_client, identity: str, limit_per_min: int) -> tuple[bool, int]:
    """Returns (allowed, remaining). Allowed=False means 429 should be returned."""
    if limit_per_min <= 0:
        return True, -1
    now_ms = int(time.time() * 1000)
    window_start = now_ms - (WINDOW_SECONDS * 1000)
    key = REDIS_KEY_PREFIX + identity
    # Purge old entries
    await redis_client.zremrangebyscore(key, 0, window_start)
    count = await redis_client.zcard(key)
    if count >= limit_per_min:
        return False, 0
    # Add new entry with unique member (timestamp + random suffix handled by score)
    await redis_client.zadd(key, {f"{now_ms}": now_ms})
    await redis_client.expire(key, WINDOW_SECONDS + 5)
    return True, limit_per_min - count - 1


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware that enforces per-identity rate limits via Redis."""

    def __init__(self, app, redis_url: str | None = None, limit_per_min: int | None = None):
        super().__init__(app)
        self._redis_url = redis_url or settings.REDIS_URL
        self._limit = limit_per_min if limit_per_min is not None else settings.RATE_LIMIT_PER_MINUTE
        self._client: aioredis.Redis | None = None

    async def _get_client(self) -> aioredis.Redis:
        if self._client is None:
            self._client = aioredis.from_url(self._redis_url, decode_responses=True)
        return self._client

    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip rate-limiting for health checks and openapi docs
        path = request.url.path
        if path.startswith("/api/v1/health") or path.startswith("/docs") or path.startswith("/openapi"):
            return await call_next(request)
        if self._limit <= 0:
            return await call_next(request)
        ident = _identity(request)
        try:
            client = await self._get_client()
            allowed, remaining = await check_rate_limit(client, ident, self._limit)
        except Exception as exc:
            # Fail open: never block the user on redis failure.
            logger.warning("rate-limit redis error identity=%s err=%s", ident, exc)
            return await call_next(request)
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again in a minute."},
                headers={"Retry-After": str(WINDOW_SECONDS), "X-RateLimit-Limit": str(self._limit)},
            )
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self._limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
