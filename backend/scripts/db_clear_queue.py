"""
Auditex -- Clear Stuck Queue
Force-fails tasks stuck in QUEUED/EXECUTING/REVIEWING/FINALISING > N minutes.

Run:
  powershell -ExecutionPolicy Bypass -File run.ps1 -cmd "docker compose exec api python scripts/db_clear_queue.py"

Optional: pass minutes threshold (default 5)
  powershell -ExecutionPolicy Bypass -File run.ps1 -cmd "docker compose exec api python scripts/db_clear_queue.py 3"
"""
import asyncio, os, sys
sys.path.insert(0, '/app')

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy import text

SEP = "-" * 50

async def run(threshold_minutes: int = 5):
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        print("ERROR: DATABASE_URL not set"); return

    engine = create_async_engine(db_url, echo=False)
    async with AsyncSession(engine) as s:

        # ── 1. Show what we are about to clear ───────────────────────────────
        stuck = (await s.execute(text(f"""
            SELECT id, task_type, status,
                   ROUND(EXTRACT(EPOCH FROM (NOW()-created_at))/60) as age_min
            FROM tasks
            WHERE status IN ('QUEUED','EXECUTING','REVIEWING','FINALISING')
            AND created_at < NOW() - INTERVAL '{threshold_minutes} minutes'
            ORDER BY created_at ASC
        """))).fetchall()

        if not stuck:
            print(f"\n  Queue is healthy — no stuck tasks found (threshold: >{threshold_minutes} min)\n")
            await engine.dispose()
            return

        print(f"\n  Found {len(stuck)} stuck task(s) (>{threshold_minutes} min in active state):")
        print("  " + SEP)
        for r in stuck:
            print(f"  {str(r.id)[:8]}  {r.task_type:<16}  {r.status:<12}  age={int(r.age_min)}min")

        # ── 2. Force-fail them ────────────────────────────────────────────────
        print(f"\n  Force-failing {len(stuck)} task(s)...")

        result = await s.execute(text(f"""
            UPDATE tasks
            SET status        = 'FAILED',
                error_message = 'Force-failed by db_clear_queue.py — stuck in active state',
                updated_at    = NOW()
            WHERE status IN ('QUEUED','EXECUTING','REVIEWING','FINALISING')
            AND created_at < NOW() - INTERVAL '{threshold_minutes} minutes'
        """))
        await s.commit()

        # ── 3. Confirm actual rows updated ───────────────────────────────────
        rows_updated = result.rowcount
        print(f"\n  RESULT: {rows_updated} row(s) updated in database")

        if rows_updated != len(stuck):
            print(f"  WARNING: Expected {len(stuck)} updates but got {rows_updated} — check for concurrent writes")
        else:
            print(f"  OK: All {rows_updated} tasks marked FAILED as expected")

        # ── 4. Post-clear status counts ───────────────────────────────────────
        counts = (await s.execute(text("""
            SELECT status, COUNT(*) as cnt
            FROM tasks GROUP BY status ORDER BY cnt DESC
        """))).fetchall()
        print(f"\n  Updated status counts:")
        print("  " + SEP)
        for r in counts:
            print(f"    {r.status:<12}  {int(r.cnt):>4}")

        # ── 5. Confirm active pipeline is now clear ───────────────────────────
        active = (await s.execute(text("""
            SELECT COUNT(*) FROM tasks
            WHERE status IN ('QUEUED','EXECUTING','REVIEWING','FINALISING')
        """))).scalar()

        print(f"\n  Active in pipeline now: {active}")
        if int(active) == 0:
            print("  CLEAR: Queue is empty. Safe to run Playwright tests.")
        else:
            print(f"  WARNING: {active} task(s) still active (may be currently processing)")
            print("  Wait 90s then re-run this script if they do not complete.")
        print()

    await engine.dispose()

threshold = int(sys.argv[1]) if len(sys.argv) > 1 else 5
asyncio.run(run(threshold))
