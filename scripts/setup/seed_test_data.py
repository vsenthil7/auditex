"""
Auditex -- Phase 2 seed script.
Run inside the API container to create:
  1. Test API key in Redis:  auditex-test-key-phase2
  2. System agent in DB:     Auditex System Agent

Usage (from project root):
  powershell -ExecutionPolicy Bypass -File run.ps1 -cmd "docker compose exec api python scripts/setup/seed_test_data.py"

Expected output:
  [SEED] Redis API key created: auditex-test-key-phase2
  [SEED] System agent created: <uuid>
  [SEED] Done.
"""
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure backend/ is on sys.path when run inside container
sys.path.insert(0, "/app")

import redis.asyncio as aioredis

from app.config import settings
from db.connection import AsyncSessionLocal
from db.repositories.agent_repo import create_agent, get_agent_by_name


TEST_API_KEY = "auditex-test-key-phase2"
SYSTEM_AGENT_NAME = "Auditex System Agent"


async def seed_redis_key(redis: aioredis.Redis) -> None:
    """Create the test API key in Redis. Idempotent -- safe to run multiple times."""
    key = f"apikey:{TEST_API_KEY}"
    existing = await redis.get(key)
    if existing:
        print(f"[SEED] Redis key already exists: {TEST_API_KEY}")
        return

    payload = json.dumps({
        "key_id": "test-phase2",
        "name": "Phase 2 Test Key",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    await redis.set(key, payload)
    print(f"[SEED] Redis API key created: {TEST_API_KEY}")


async def seed_system_agent() -> None:
    """Create the system agent in DB. Idempotent -- skips if already exists."""
    async with AsyncSessionLocal() as session:
        existing = await get_agent_by_name(session, SYSTEM_AGENT_NAME)
        if existing:
            print(f"[SEED] System agent already exists: {existing.id}")
            await session.commit()
            return

        agent = await create_agent(
            session,
            name=SYSTEM_AGENT_NAME,
            agent_type="system",
            model_version=None,
            capabilities=["task_routing", "health_monitoring"],
            metadata={"created_by": "seed_test_data.py", "phase": "2"},
        )
        await session.commit()
        print(f"[SEED] System agent created: {agent.id}")


async def main() -> None:
    redis = aioredis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
    )
    try:
        await seed_redis_key(redis)
    finally:
        await redis.aclose()

    await seed_system_agent()
    print("[SEED] Done.")


if __name__ == "__main__":
    asyncio.run(main())
