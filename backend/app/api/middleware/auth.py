"""
Auditex -- API key authentication middleware.

Phase 2: Redis-backed X-API-Key validation.
A valid key must exist in Redis under the key: apikey:{key_value}
Value stored is a JSON object: {"key_id": "...", "created_at": "..."}

The seed script (scripts/setup/seed_test_data.py) creates:
  apikey:auditex-test-key-phase2 -> {"key_id": "test-phase2", "created_at": "..."}

Phase 4 will add JWT validation and per-key rate limiting.
"""
import json
import logging

import redis.asyncio as aioredis
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.config import settings

logger = logging.getLogger(__name__)

# FastAPI security scheme -- reads X-API-Key header
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# Redis client -- module-level singleton (lazy connection)
_redis_client: aioredis.Redis | None = None


def _get_redis() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_client


async def require_api_key(
    api_key: str | None = Security(api_key_header),
) -> dict:
    """
    FastAPI dependency. Validates X-API-Key against Redis.
    Returns the key metadata dict on success.
    Raises HTTP 401 if key is missing or invalid.

    Usage:
        @router.get("/endpoint")
        async def handler(key_meta: dict = Depends(require_api_key)):
            ...
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    redis = _get_redis()
    try:
        raw = await redis.get(f"apikey:{api_key}")
    except Exception as e:
        logger.error("Redis error during API key validation: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service temporarily unavailable.",
        )

    if raw is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    try:
        key_meta = json.loads(raw)
    except json.JSONDecodeError:
        logger.error("Corrupted API key record in Redis for key hash")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication data corrupted.",
        )

    return key_meta
