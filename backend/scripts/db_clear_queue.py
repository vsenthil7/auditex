"""
Auditex -- Clear Stuck Queue + Full Status Report
Uses psycopg2 directly (synchronous) — avoids asyncpg event loop issues in scripts.

Run:
  powershell -ExecutionPolicy Bypass -File run.ps1 -cmd "docker compose exec api python scripts/db_clear_queue.py"

Optional threshold in minutes (default 5):
  powershell -ExecutionPolicy Bypass -File run.ps1 -cmd "docker compose exec api python scripts/db_clear_queue.py 3"
"""
import os, sys, re
sys.path.insert(0, '/app')

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print("ERROR: psycopg2 not available. Trying pip install...")
    os.system("pip install psycopg2-binary -q")
    import psycopg2
    import psycopg2.extras

import datetime

SEP  = "=" * 60
SEP2 = "-" * 50

def get_conn():
    """Build a synchronous psycopg2 connection from DATABASE_URL env var."""
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        raise RuntimeError("DATABASE_URL not set in environment")
    # Convert asyncpg URL to psycopg2 format
    # postgresql+asyncpg://user:pass@host:port/db -> postgresql://user:pass@host:port/db
    url = url.replace("postgresql+asyncpg://", "postgresql://")
    return psycopg2.connect(url)

def run(mins: int = 5):
    print()
    print(SEP)
    print(f"  db_clear_queue.py  threshold={mins}min  {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(SEP)
    sys.stdout.flush()

    conn = get_conn()
    conn.autocommit = False
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        # ── 1. Find stuck tasks ───────────────────────────────────────────────
        cur.execute("""
            SELECT id, task_type, status,
                   ROUND(EXTRACT(EPOCH FROM (NOW()-created_at))/60)::int AS age_min
            FROM tasks
            WHERE status IN ('QUEUED','EXECUTING','REVIEWING','FINALISING')
            AND created_at < NOW() - (%s * INTERVAL '1 minute')
            ORDER BY created_at ASC
        """, (mins,))
        stuck = cur.fetchall()

        if not stuck:
            print(f"\n  RESULT: Queue is healthy — no stuck tasks (>{mins} min)")
            sys.stdout.flush()
        else:
            print(f"\n  FOUND: {len(stuck)} stuck task(s) (>{mins} min in active state)")
            print("  " + SEP2)
            for r in stuck:
                print(f"  {str(r['id'])[:8]}  {r['task_type']:<16}  {r['status']:<12}  age={r['age_min']}min")
            sys.stdout.flush()

            # ── 2. Force-fail them ────────────────────────────────────────────
            print(f"\n  ACTION: Force-failing {len(stuck)} task(s)...")
            sys.stdout.flush()

            cur.execute("""
                UPDATE tasks
                SET status        = 'FAILED',
                    error_message = 'Force-failed by db_clear_queue.py — stuck in active state',
                    updated_at    = NOW()
                WHERE status IN ('QUEUED','EXECUTING','REVIEWING','FINALISING')
                AND created_at < NOW() - (%s * INTERVAL '1 minute')
            """, (mins,))

            rows_updated = cur.rowcount
            conn.commit()

            # ── 3. Confirm rows updated ───────────────────────────────────────
            print(f"  UPDATED: {rows_updated} row(s) written to database")
            if rows_updated == len(stuck):
                print(f"  OK: All {rows_updated} tasks marked FAILED as expected")
            else:
                print(f"  WARNING: Expected {len(stuck)} but updated {rows_updated}")
            sys.stdout.flush()

        # ── 4. Post-clear status counts ───────────────────────────────────────
        print()
        print(SEP)
        print("  POST-CLEAR STATUS REPORT")
        print(SEP)
        sys.stdout.flush()

        cur.execute("SELECT status, COUNT(*) as cnt FROM tasks GROUP BY status ORDER BY cnt DESC")
        counts = cur.fetchall()
        print("\n  TASK STATUS COUNTS")
        print("  " + SEP2)
        for r in counts:
            bar = "#" * min(int(r['cnt']), 30)
            print(f"  {r['status']:<12}  {int(r['cnt']):>4}  {bar}")
        sys.stdout.flush()

        cur.execute("""
            SELECT COUNT(*) as cnt FROM tasks
            WHERE status IN ('QUEUED','EXECUTING','REVIEWING','FINALISING')
        """)
        active = cur.fetchone()['cnt']
        print(f"\n  ACTIVE IN PIPELINE: {active}")
        if active == 0:
            print("  STATUS: CLEAR — safe to submit tasks and run Playwright")
        else:
            print(f"  STATUS: {active} task(s) still active (may be currently processing)")
            print("  Wait 90s and re-run if they do not complete")
        sys.stdout.flush()

        # ── 5. Last 10 tasks ──────────────────────────────────────────────────
        cur.execute("""
            SELECT id, task_type, status, created_at, report_available,
                   CASE WHEN executor_output_json IS NOT NULL THEN 'Y' ELSE 'N' END AS ex,
                   CASE WHEN review_result_json   IS NOT NULL THEN 'Y' ELSE 'N' END AS rev,
                   CASE WHEN vertex_event_hash    IS NOT NULL THEN 'Y' ELSE 'N' END AS vtx
            FROM tasks ORDER BY created_at DESC LIMIT 10
        """)
        rows = cur.fetchall()
        print(f"\n  LAST 10 TASKS")
        print("  " + SEP2)
        print(f"  {'ID':8}  {'TYPE':16}  {'STATUS':12}  {'RPT':5}  EX  REV  VTX  TIME")
        print("  " + SEP2)
        for r in rows:
            t = r['created_at'].strftime("%H:%M") if r['created_at'] else "?"
            print(f"  {str(r['id'])[:8]}  {r['task_type']:<16}  {r['status']:<12}  {str(r['report_available']):5}  {r['ex']:2}  {r['rev']:3}  {r['vtx']:3}  {t}")
        sys.stdout.flush()

        # ── 6. Reports ────────────────────────────────────────────────────────
        cur.execute("SELECT COUNT(*) as cnt FROM reports")
        rcount = cur.fetchone()['cnt']
        print(f"\n  REPORTS IN DB: {rcount}")
        sys.stdout.flush()

        print()
        print(SEP)
        print("  DONE")
        print(SEP)
        print()
        sys.stdout.flush()

    finally:
        cur.close()
        conn.close()

mins = int(sys.argv[1]) if len(sys.argv) > 1 else 5
run(mins)
