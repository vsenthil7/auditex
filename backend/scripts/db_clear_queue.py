"""
Auditex -- Clear Stuck Queue
Force-fails tasks stuck in QUEUED/EXECUTING/REVIEWING/FINALISING > N minutes.
Safe to run — only affects tasks that are genuinely stuck.

Run:
  powershell -ExecutionPolicy Bypass -File run.ps1 -cmd "docker compose exec api python scripts/db_clear_queue.py"

Optional: pass minutes threshold (default 5)
  powershell -ExecutionPolicy Bypass -File run.ps1 -cmd "docker compose exec api python scripts/db_clear_queue.py 3"
"""
import asyncio, os, sys
sys.path.insert(0, '/app')

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy import text

async def run(threshold_minutes: int = 5):
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        print("ERROR: DATABASE_URL not set"); return

    engine = create_async_engine(db_url, echo=False)
    async with AsyncSession(engine) as s:

        # Show what we are about to clear
        stuck = (await s.execute(text("""
            SELECT id, task_type, status,
                   ROUND(EXTRACT(EPOCH FROM (NOW()-created_at))/60) as age_min
            FROM tasks
            WHERE status IN ('QUEUED','EXECUTING','REVIEWING','FINALISING')
            AND created_at < NOW() - INTERVAL ':mins minutes'
            ORDER BY created_at ASC
        """.replace(':mins', str(threshold_minutes))))
        ).fetchall()

        if not stuck:
            print(f"\n  No stuck tasks found (threshold: >{threshold_minutes} min). Queue is healthy.\n")
            await engine.dispose()
            return

        print(f"\n  Found {len(stuck)} stuck task(s) (>{threshold_minutes} min in active state):")
        print("  " + "-"*50)
        for r in stuck:
            print(f"  {str(r.id)[:8]}  {r.task_type:<16}  {r.status:<12}  age={int(r.age_min)}min")

        print(f"\n  Force-failing {len(stuck)} task(s)...")

        result = await s.execute(text("""
            UPDATE tasks
            SET status = 'FAILED',
                error_message = 'Force-failed by db_clear_queue.py — task was stuck in active state',
                updated_at = NOW()
            WHERE status IN ('QUEUED','EXECUTING','REVIEWING','FINALISING')
            AND created_at < NOW() - INTERVAL ':mins minutes'
        """.replace(':mins', str(threshold_minutes))))
        await s.commit()

        print(f"  Done. {result.rowcount} task(s) marked FAILED.")

        # Confirm new counts
        counts = (await s.execute(text("""
            SELECT status, COUNT(*) as cnt FROM tasks GROUP BY status ORDER BY cnt DESC
        """))).fetchall()
        print(f"\n  Updated status counts:")
        for r in counts:
            print(f"    {r.status:<12} {int(r.cnt)}")

        active = (await s.execute(text("""
            SELECT COUNT(*) FROM tasks
            WHERE status IN ('QUEUED','EXECUTING','REVIEWING','FINALISING')
        """))).scalar()
        print(f"\n  Active in pipeline now: {active}")
        if int(active) == 0:
            print("  Queue is clear. Safe to run Playwright tests.")
        print()

    await engine.dispose()

threshold = int(sys.argv[1]) if len(sys.argv) > 1 else 5
asyncio.run(run(threshold))
