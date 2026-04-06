"""
Auditex -- Queue + DB Status Check
Shows: queue depth, task status counts, last 10 tasks, any stuck tasks.

Run:
  powershell -ExecutionPolicy Bypass -File run.ps1 -cmd "docker compose exec postgres psql -U auditex -d auditex -f /dev/stdin" < backend/scripts/db_status.sql

OR via python (reads from container env):
  powershell -ExecutionPolicy Bypass -File run.ps1 -cmd "docker compose exec api python scripts/db_status.py"
"""
import asyncio, os, sys, json
sys.path.insert(0, '/app')

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy import text

async def run():
    db_url = os.environ.get("DATABASE_URL","")
    if not db_url:
        print("ERROR: DATABASE_URL not set"); return
    engine = create_async_engine(db_url, echo=False)
    async with AsyncSession(engine) as s:

        print("\n" + "="*60)
        print("  AUDITEX DB STATUS  " + __import__('datetime').datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
        print("="*60)

        # 1. Status counts
        rows = (await s.execute(text("""
            SELECT status, COUNT(*) as cnt
            FROM tasks GROUP BY status ORDER BY cnt DESC
        """))).fetchall()
        print("\n── TASK STATUS COUNTS ──────────────────────────────────")
        for r in rows:
            bar = "█" * min(int(r.cnt), 30)
            print(f"  {r.status:<12} {r.cnt:>4}  {bar}")

        # 2. Queue depth (QUEUED + EXECUTING + REVIEWING + FINALISING)
        active = (await s.execute(text("""
            SELECT COUNT(*) as cnt FROM tasks
            WHERE status IN ('QUEUED','EXECUTING','REVIEWING','FINALISING')
        """))).scalar()
        print(f"\n── ACTIVE IN PIPELINE: {active} task(s) ─────────────────────")
        if active > 0:
            print("  WARNING: Tasks in queue — Playwright TC-02 will wait for these first")

        # 3. Last 10 tasks newest first
        rows = (await s.execute(text("""
            SELECT id, task_type, status, created_at, updated_at,
                   report_available,
                   CASE WHEN executor_output_json IS NOT NULL THEN 'YES' ELSE 'NO' END as has_executor,
                   CASE WHEN review_result_json   IS NOT NULL THEN 'YES' ELSE 'NO' END as has_review,
                   CASE WHEN vertex_event_hash    IS NOT NULL THEN 'YES' ELSE 'NO' END as has_vertex
            FROM tasks ORDER BY created_at DESC LIMIT 10
        """))).fetchall()
        print("\n── LAST 10 TASKS (newest first) ────────────────────────")
        print(f"  {'ID':<10} {'TYPE':<16} {'STATUS':<12} {'REPORT':<8} {'EXEC':<6} {'REVIEW':<8} {'VERTEX':<8} CREATED")
        print("  " + "-"*90)
        for r in rows:
            tid = str(r.id)[:8]
            created = r.created_at.strftime("%H:%M:%S") if r.created_at else "?"
            print(f"  {tid:<10} {r.task_type:<16} {r.status:<12} {str(r.report_available):<8} {r.has_executor:<6} {r.has_review:<8} {r.has_vertex:<8} {created}")

        # 4. Reports table
        report_count = (await s.execute(text("SELECT COUNT(*) FROM reports"))).scalar()
        print(f"\n── REPORTS TABLE: {report_count} report(s) ──────────────────────────")
        if report_count > 0:
            rrows = (await s.execute(text("""
                SELECT r.id, r.task_id, r.generated_at, r.generator_model,
                       CASE WHEN r.narrative IS NOT NULL THEN 'YES' ELSE 'NO' END as has_narrative,
                       CASE WHEN r.eu_ai_act_json IS NOT NULL THEN 'YES' ELSE 'NO' END as has_eu_act,
                       t.status as task_status
                FROM reports r
                JOIN tasks t ON t.id = r.task_id
                ORDER BY r.generated_at DESC LIMIT 5
            """))).fetchall()
            print(f"  {'REPORT_ID':<10} {'TASK_ID':<10} {'NARRATIVE':<10} {'EU_ACT':<8} {'TASK_STATUS':<12} GENERATED")
            print("  " + "-"*70)
            for r in rrows:
                rid = str(r.id)[:8]
                tid = str(r.task_id)[:8]
                gen = r.generated_at.strftime("%H:%M:%S") if r.generated_at else "?"
                print(f"  {rid:<10} {tid:<10} {r.has_narrative:<10} {r.has_eu_act:<8} {r.task_status:<12} {gen}")

        # 5. Stuck tasks (QUEUED/EXECUTING > 5 min)
        stuck = (await s.execute(text("""
            SELECT id, task_type, status, created_at,
                   EXTRACT(EPOCH FROM (NOW() - created_at))/60 as age_minutes
            FROM tasks
            WHERE status IN ('QUEUED','EXECUTING','REVIEWING','FINALISING')
            AND created_at < NOW() - INTERVAL '5 minutes'
            ORDER BY created_at ASC
        """))).fetchall()
        if stuck:
            print(f"\n── STUCK TASKS (>5 min in active state) ───────────────")
            for r in stuck:
                print(f"  {str(r.id)[:8]}… {r.task_type} {r.status} age={r.age_minutes:.0f}min")
        else:
            print(f"\n── NO STUCK TASKS ──────────────────────────────────────")

        print("\n" + "="*60 + "\n")
    await engine.dispose()

asyncio.run(run())
