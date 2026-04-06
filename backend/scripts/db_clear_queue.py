"""
Auditex -- Clear Stuck Queue
Force-fails tasks stuck in QUEUED/EXECUTING/REVIEWING/FINALISING > N minutes.
Runs a full status report at the end — no need to run db_status.py separately.

Run:
  powershell -ExecutionPolicy Bypass -File run.ps1 -cmd "docker compose exec api python scripts/db_clear_queue.py"

Optional: pass minutes threshold (default 5)
  powershell -ExecutionPolicy Bypass -File run.ps1 -cmd "docker compose exec api python scripts/db_clear_queue.py 3"
"""
import asyncio, os, sys
sys.path.insert(0, '/app')

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy import text

SEP  = "=" * 60
SEP2 = "-" * 50

async def run(mins: int = 5):
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        print("ERROR: DATABASE_URL not set")
        return

    engine = create_async_engine(db_url, echo=False)
    async with AsyncSession(engine) as s:

        import datetime
        print()
        print(SEP)
        print(f"  db_clear_queue.py  threshold={mins}min  {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        print(SEP)

        # ── 1. Find stuck tasks ───────────────────────────────────────────────
        stuck_rows = (await s.execute(text(
            "SELECT id, task_type, status, "
            "ROUND(EXTRACT(EPOCH FROM (NOW()-created_at))/60) as age_min "
            "FROM tasks "
            "WHERE status IN ('QUEUED','EXECUTING','REVIEWING','FINALISING') "
            "AND created_at < NOW() - (:mins * INTERVAL '1 minute') "
            "ORDER BY created_at ASC"
        ), {"mins": mins})).fetchall()

        if not stuck_rows:
            print(f"\n  RESULT: Queue is healthy — no stuck tasks (>{mins} min)")
        else:
            print(f"\n  FOUND: {len(stuck_rows)} stuck task(s) (>{mins} min in active state)")
            print("  " + SEP2)
            for r in stuck_rows:
                print(f"  {str(r.id)[:8]}  {r.task_type:<16}  {r.status:<12}  age={int(r.age_min)}min")

            # ── 2. Force-fail them ────────────────────────────────────────────
            print(f"\n  ACTION: Force-failing {len(stuck_rows)} task(s)...")

            result = await s.execute(text(
                "UPDATE tasks "
                "SET status = 'FAILED', "
                "    error_message = 'Force-failed by db_clear_queue.py — stuck in active state', "
                "    updated_at = NOW() "
                "WHERE status IN ('QUEUED','EXECUTING','REVIEWING','FINALISING') "
                "AND created_at < NOW() - (:mins * INTERVAL '1 minute')"
            ), {"mins": mins})
            await s.commit()

            # ── 3. Confirm rows updated ───────────────────────────────────────
            rows_updated = result.rowcount
            print(f"  UPDATED: {rows_updated} row(s) written to database")

            if rows_updated == len(stuck_rows):
                print(f"  OK: All {rows_updated} tasks marked FAILED as expected")
            else:
                print(f"  WARNING: Expected {len(stuck_rows)} but updated {rows_updated} — possible concurrent write")

        # ── 4. Full status report (replaces need to run db_status.py) ─────────
        print()
        print(SEP)
        print("  POST-CLEAR STATUS REPORT")
        print(SEP)

        counts = (await s.execute(text(
            "SELECT status, COUNT(*) as cnt FROM tasks GROUP BY status ORDER BY cnt DESC"
        ))).fetchall()
        print("\n  TASK STATUS COUNTS")
        print("  " + SEP2)
        for r in counts:
            bar = "#" * min(int(r.cnt), 30)
            print(f"  {r.status:<12}  {int(r.cnt):>4}  {bar}")

        active = (await s.execute(text(
            "SELECT COUNT(*) FROM tasks "
            "WHERE status IN ('QUEUED','EXECUTING','REVIEWING','FINALISING')"
        ))).scalar()
        print(f"\n  ACTIVE IN PIPELINE : {int(active)}")

        if int(active) == 0:
            print("  STATUS: Queue is CLEAR. Safe to submit tasks and run Playwright.")
        else:
            print(f"  STATUS: {active} task(s) still active (may be currently processing)")
            print("  Wait 90s and re-run this script if they do not complete.")

        last10 = (await s.execute(text(
            "SELECT id, task_type, status, created_at, report_available, "
            "CASE WHEN executor_output_json IS NOT NULL THEN 'Y' ELSE 'N' END as ex, "
            "CASE WHEN review_result_json   IS NOT NULL THEN 'Y' ELSE 'N' END as rev, "
            "CASE WHEN vertex_event_hash    IS NOT NULL THEN 'Y' ELSE 'N' END as vtx "
            "FROM tasks ORDER BY created_at DESC LIMIT 10"
        ))).fetchall()
        print(f"\n  LAST 10 TASKS")
        print("  " + SEP2)
        print(f"  {'ID':8}  {'TYPE':16}  {'STATUS':12}  {'RPT':5}  EX  REV  VTX  TIME")
        print("  " + SEP2)
        for r in last10:
            t = r.created_at.strftime("%H:%M") if r.created_at else "?"
            print(f"  {str(r.id)[:8]}  {r.task_type:<16}  {r.status:<12}  {str(r.report_available):5}  {r.ex:2}  {r.rev:3}  {r.vtx:3}  {t}")

        rcount = (await s.execute(text("SELECT COUNT(*) FROM reports"))).scalar()
        print(f"\n  REPORTS IN DB: {rcount}")

        print()
        print(SEP)
        print("  DONE")
        print(SEP)
        print()

    await engine.dispose()

mins = int(sys.argv[1]) if len(sys.argv) > 1 else 5
asyncio.run(run(mins))
