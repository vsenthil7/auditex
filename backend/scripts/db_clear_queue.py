"""
Auditex -- Clear Stuck Queue + Full Status Report
Runs directly via: docker compose exec api python scripts/db_clear_queue.py

Uses urllib + asyncpg via a raw subprocess psql call — no extra dependencies.
Actually uses the simplest possible approach: subprocess psql which is
guaranteed available since postgres is the DB container.
"""
import os, sys, subprocess, datetime

SEP  = "=" * 60
SEP2 = "-" * 50

def psql(sql, params=None):
    """Run SQL via psql subprocess — guaranteed to work in any container."""
    db_url = os.environ.get("DATABASE_URL", "").replace("postgresql+asyncpg://", "postgresql://")
    if not db_url:
        raise RuntimeError("DATABASE_URL not set")
    cmd = ["psql", db_url, "-c", sql, "--no-align", "--tuples-only", "--field-separator=|"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"psql error: {result.stderr}")
    rows = []
    for line in result.stdout.strip().splitlines():
        if line.strip():
            rows.append(line.split("|"))
    return rows

def psql_exec(sql):
    """Run a DML statement via psql, return rowcount from output."""
    db_url = os.environ.get("DATABASE_URL", "").replace("postgresql+asyncpg://", "postgresql://")
    cmd = ["psql", db_url, "-c", sql]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"psql error: {result.stderr}")
    # psql prints "UPDATE 8" etc
    out = result.stdout.strip()
    print(f"  DB RESPONSE: {out}")
    sys.stdout.flush()
    # Parse rowcount
    for line in out.splitlines():
        parts = line.strip().split()
        if len(parts) == 2 and parts[1].isdigit():
            return int(parts[1])
    return -1

def run(mins=5):
    print()
    print(SEP)
    print(f"  db_clear_queue.py  threshold={mins}min  {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(SEP)
    sys.stdout.flush()

    # 1. Find stuck tasks
    rows = psql(f"""
        SELECT id::text, task_type, status,
               ROUND(EXTRACT(EPOCH FROM (NOW()-created_at))/60)::int
        FROM tasks
        WHERE status IN ('QUEUED','EXECUTING','REVIEWING','FINALISING')
        AND created_at < NOW() - ({mins} * INTERVAL '1 minute')
        ORDER BY created_at ASC
    """)

    if not rows:
        print(f"\n  RESULT: Queue healthy — no stuck tasks (>{mins} min)")
        sys.stdout.flush()
    else:
        print(f"\n  FOUND: {len(rows)} stuck task(s)")
        print("  " + SEP2)
        for r in rows:
            print(f"  {r[0][:8]}  {r[1]:<16}  {r[2]:<12}  age={r[3]}min")
        sys.stdout.flush()

        print(f"\n  ACTION: Force-failing {len(rows)} task(s)...")
        sys.stdout.flush()

        updated = psql_exec(f"""
            UPDATE tasks
            SET status='FAILED',
                error_message='Force-failed by db_clear_queue.py',
                updated_at=NOW()
            WHERE status IN ('QUEUED','EXECUTING','REVIEWING','FINALISING')
            AND created_at < NOW() - ({mins} * INTERVAL '1 minute')
        """)

        if updated == len(rows):
            print(f"  OK: {updated} tasks marked FAILED")
        elif updated == -1:
            print(f"  CHECK: Could not parse rowcount — verify manually")
        else:
            print(f"  WARNING: Expected {len(rows)} updates, got {updated}")
        sys.stdout.flush()

    # 2. Status counts
    print()
    print(SEP)
    print("  POST-CLEAR STATUS REPORT")
    print(SEP)
    sys.stdout.flush()

    counts = psql("SELECT status, COUNT(*) FROM tasks GROUP BY status ORDER BY COUNT(*) DESC")
    print("\n  STATUS COUNTS")
    print("  " + SEP2)
    for r in counts:
        bar = "#" * min(int(r[1]), 30)
        print(f"  {r[0]:<12}  {r[1]:>4}  {bar}")
    sys.stdout.flush()

    active = psql("SELECT COUNT(*) FROM tasks WHERE status IN ('QUEUED','EXECUTING','REVIEWING','FINALISING')")
    active_count = int(active[0][0]) if active else 0
    print(f"\n  ACTIVE IN PIPELINE: {active_count}")
    print("  STATUS: CLEAR — safe to run Playwright" if active_count == 0 else f"  STATUS: {active_count} still active")
    sys.stdout.flush()

    # 3. Last 10 tasks
    last10 = psql("""
        SELECT id::text, task_type, status,
               to_char(created_at,'HH24:MI'),
               report_available::text,
               CASE WHEN executor_output_json IS NOT NULL THEN 'Y' ELSE 'N' END,
               CASE WHEN review_result_json   IS NOT NULL THEN 'Y' ELSE 'N' END,
               CASE WHEN vertex_event_hash    IS NOT NULL THEN 'Y' ELSE 'N' END
        FROM tasks ORDER BY created_at DESC LIMIT 10
    """)
    print(f"\n  LAST 10 TASKS")
    print("  " + SEP2)
    print(f"  {'ID':8}  {'TYPE':16}  {'STATUS':12}  {'RPT':5}  EX  REV  VTX  TIME")
    print("  " + SEP2)
    for r in last10:
        print(f"  {r[0][:8]}  {r[1]:<16}  {r[2]:<12}  {r[4]:5}  {r[5]:2}  {r[6]:3}  {r[7]:3}  {r[3]}")
    sys.stdout.flush()

    rcount = psql("SELECT COUNT(*) FROM reports")
    print(f"\n  REPORTS IN DB: {rcount[0][0] if rcount else 0}")

    print()
    print(SEP)
    print("  DONE")
    print(SEP)
    print()
    sys.stdout.flush()

mins = int(sys.argv[1]) if len(sys.argv) > 1 else 5
run(mins)
