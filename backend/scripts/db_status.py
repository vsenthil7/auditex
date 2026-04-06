"""
Auditex -- DB Status Check (ASCII only, no unicode box chars)
Shows queue depth, task counts, last 10 tasks, reports, stuck tasks.

Run:
  powershell -ExecutionPolicy Bypass -File run.ps1 -cmd "docker compose exec api python scripts/db_status.py"
"""
import asyncio, os, sys
sys.path.insert(0, '/app')

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy import text

SEP  = "=" * 60
SEP2 = "-" * 60

async def run():
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        print("ERROR: DATABASE_URL not set"); return

    engine = create_async_engine(db_url, echo=False)
    async with AsyncSession(engine) as s:

        import datetime
        print("\n" + SEP)
        print("  AUDITEX DB STATUS  " + datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
        print(SEP)

        # 1. Status counts
        rows = (await s.execute(text("""
            SELECT status, COUNT(*) as cnt
            FROM tasks GROUP BY status ORDER BY cnt DESC
        """))).fetchall()
        print("\n  TASK STATUS COUNTS")
        print("  " + SEP2)
        for r in rows:
            bar = "#" * min(int(r.cnt), 30)
            print(f"  {r.status:<12} {int(r.cnt):>4}  {bar}")

        # 2. Active pipeline count
        active = (await s.execute(text("""
            SELECT COUNT(*) FROM tasks
            WHERE status IN ('QUEUED','EXECUTING','REVIEWING','FINALISING')
        """))).scalar()
        print(f"\n  ACTIVE IN PIPELINE : {active}")
        if int(active) > 0:
            print("  NOTE: Playwright TC-02 will wait for these to finish before submitting")
            print("  TIP:  Run db_clear_queue.py to mark stuck tasks as FAILED if needed")

        # 3. Last 10 tasks
        rows = (await s.execute(text("""
            SELECT id, task_type, status, created_at,
                   report_available,
                   CASE WHEN executor_output_json IS NOT NULL THEN 'Y' ELSE 'N' END as exec,
                   CASE WHEN review_result_json   IS NOT NULL THEN 'Y' ELSE 'N' END as review,
                   CASE WHEN vertex_event_hash    IS NOT NULL THEN 'Y' ELSE 'N' END as vertex
            FROM tasks ORDER BY created_at DESC LIMIT 10
        """))).fetchall()
        print(f"\n  LAST 10 TASKS (newest first)")
        print("  " + SEP2)
        print(f"  {'ID':8}  {'TYPE':16}  {'STATUS':12}  {'RPT':4}  {'EX':3}  {'REV':4}  {'VTX':4}  TIME")
        print("  " + SEP2)
        for r in rows:
            t = r.created_at.strftime("%H:%M:%S") if r.created_at else "?"
            print(f"  {str(r.id)[:8]}  {r.task_type:<16}  {r.status:<12}  {str(r.report_available):4}  {r.exec:3}  {r.review:4}  {r.vertex:4}  {t}")

        # 4. Reports
        rcount = (await s.execute(text("SELECT COUNT(*) FROM reports"))).scalar()
        print(f"\n  REPORTS TABLE : {rcount} total")
        if int(rcount) > 0:
            rrows = (await s.execute(text("""
                SELECT r.id, r.task_id, r.generated_at,
                       CASE WHEN r.narrative     IS NOT NULL THEN 'Y' ELSE 'N' END as narr,
                       CASE WHEN r.eu_ai_act_json IS NOT NULL THEN 'Y' ELSE 'N' END as eu,
                       t.status
                FROM reports r JOIN tasks t ON t.id = r.task_id
                ORDER BY r.generated_at DESC LIMIT 5
            """))).fetchall()
            print("  " + SEP2)
            print(f"  {'RPT_ID':8}  {'TASK_ID':8}  {'NARR':5}  {'EU_ACT':7}  {'STATUS':12}  TIME")
            print("  " + SEP2)
            for r in rrows:
                t = r.generated_at.strftime("%H:%M:%S") if r.generated_at else "?"
                print(f"  {str(r.id)[:8]}  {str(r.task_id)[:8]}  {r.narr:5}  {r.eu:7}  {r.status:<12}  {t}")

        # 5. Stuck tasks > 5 min
        stuck = (await s.execute(text("""
            SELECT id, task_type, status,
                   ROUND(EXTRACT(EPOCH FROM (NOW()-created_at))/60) as age_min
            FROM tasks
            WHERE status IN ('QUEUED','EXECUTING','REVIEWING','FINALISING')
            AND created_at < NOW() - INTERVAL '5 minutes'
            ORDER BY created_at ASC
        """))).fetchall()
        print(f"\n  STUCK TASKS (>5 min active) : {len(stuck)}")
        if stuck:
            print("  " + SEP2)
            for r in stuck:
                print(f"  {str(r.id)[:8]}  {r.task_type:<16}  {r.status:<12}  age={int(r.age_min)}min")
            print(f"\n  ACTION: Run db_clear_queue.py to force-fail stuck tasks")

        print("\n" + SEP + "\n")
    await engine.dispose()

asyncio.run(run())
