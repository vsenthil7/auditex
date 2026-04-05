"""
Auditex -- Health check routes.
GET /api/v1/health       -- basic liveness (no auth required)
GET /api/v1/health/deep  -- full service check (auth required) -- MT-001
"""
import logging

import redis.asyncio as aioredis
import sqlalchemy
from fastapi import APIRouter, Depends

from app.api.middleware.auth import require_api_key
from app.config import settings
from db.connection import engine

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_basic():
    """
    Basic liveness check. No auth. Used by load balancers and Docker healthcheck.
    Returns 200 if the process is alive.
    """
    return {
        "status": "healthy",
        "version": "0.1.0",
    }


@router.get("/health/deep")
async def health_deep(_key_meta: dict = Depends(require_api_key)):
    """
    Deep health check. Requires X-API-Key.
    Tests real connectivity to every backing service.
    MT-001 expected response:
    {
      "status": "healthy",
      "version": "0.1.0",
      "services": {
        "database": "connected",
        "redis": "connected",
        "foxmq": "connected",
        "vertex": "not_connected"
      },
      "database_tables": ["agents","tasks","audit_events","reports"]
    }
    """
    db_status = "not_connected"
    redis_status = "not_connected"
    foxmq_status = "not_connected"
    db_tables: list[str] = []

    # --- Database ---
    try:
        async with engine.connect() as conn:
            await conn.execute(sqlalchemy.text("SELECT 1"))
            # Check expected tables exist
            result = await conn.execute(sqlalchemy.text(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public' "
                "ORDER BY tablename"
            ))
            db_tables = [row[0] for row in result.fetchall()]
        db_status = "connected"
    except Exception as e:
        logger.warning("Health deep -- DB check failed: %s", e)
        db_status = f"error: {str(e)[:80]}"

    # --- Redis ---
    try:
        r = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        await r.ping()
        await r.aclose()
        redis_status = "connected"
    except Exception as e:
        logger.warning("Health deep -- Redis check failed: %s", e)
        redis_status = f"error: {str(e)[:80]}"

    # --- FoxMQ (MQTT broker) ---
    # Phase 2: TCP connect check to MQTT port. Full MQTT handshake in Phase 3.
    try:
        import asyncio
        host = "foxmq"
        port = 1883
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=2.0
        )
        writer.close()
        await writer.wait_closed()
        foxmq_status = "connected"
    except Exception as e:
        logger.warning("Health deep -- FoxMQ check failed: %s", e)
        foxmq_status = f"error: {str(e)[:80]}"

    # Filter to the four expected compliance tables
    expected_tables = {"agents", "tasks", "audit_events", "reports"}
    compliance_tables = sorted([t for t in db_tables if t in expected_tables])

    all_healthy = (
        db_status == "connected"
        and redis_status == "connected"
    )

    return {
        "status": "healthy" if all_healthy else "degraded",
        "version": "0.1.0",
        "services": {
            "database": db_status,
            "redis": redis_status,
            "foxmq": foxmq_status,
            "vertex": "not_connected",  # Phase 3
        },
        "database_tables": compliance_tables,
    }
