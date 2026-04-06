"""
Auditex -- Backend Data Verification Script
Shows the last 5 tasks (or a specific task) with full DB content.

Run:
  powershell -ExecutionPolicy Bypass -File run.ps1 -cmd "docker compose exec api python scripts/verify_task_data.py"

Specific task:
  powershell -ExecutionPolicy Bypass -File run.ps1 -cmd "docker compose exec api python scripts/verify_task_data.py <task_id>"
"""
from __future__ import annotations

import asyncio
import json
import sys
import os

# Must set PYTHONPATH so imports resolve inside the container
sys.path.insert(0, '/app')
os.environ.setdefault('PYTHONPATH', '/app')

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy import text

SEP = "─" * 68

def j(raw):
    """Parse + pretty-print JSON, truncated at 800 chars."""
    if not raw:
        return "  NULL"
    try:
        parsed = json.loads(raw)
        out = json.dumps(parsed, indent=2)
        return out[:800] + ("\n  …(truncated)" if len(out) > 800 else "")
    except Exception as e:
        return f"  PARSE ERROR: {e}\n  RAW: {str(raw)[:200]}"

async def run(task_id: str | None):
    # Read DB URL from environment (already set in the container)
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        print("ERROR: DATABASE_URL not set in environment.")
        return

    engine = create_async_engine(db_url, echo=False)

    async with AsyncSession(engine) as s:
        # ── Tasks ────────────────────────────────────────────────────────────
        if task_id:
            rows = (await s.execute(text("""
                SELECT id, task_type, status, created_at, updated_at,
                       payload_json, executor_output_json, review_result_json,
                       vertex_event_hash, vertex_round, vertex_finalised_at,
                       report_available, error_message
                FROM tasks WHERE id = :tid
            """), {"tid": task_id})).fetchall()
        else:
            rows = (await s.execute(text("""
                SELECT id, task_type, status, created_at, updated_at,
                       payload_json, executor_output_json, review_result_json,
                       vertex_event_hash, vertex_round, vertex_finalised_at,
                       report_available, error_message
                FROM tasks ORDER BY created_at DESC LIMIT 5
            """))).fetchall()

        if not rows:
            print("No tasks found in database.")
            await engine.dispose()
            return

        for row in rows:
            print()
            print(SEP)
            print(f"  TASK  {row.id}")
            print(SEP)
            print(f"  type             : {row.task_type}")
            print(f"  status           : {row.status}")
            print(f"  created_at       : {row.created_at}")
            print(f"  updated_at       : {row.updated_at}")
            print(f"  report_available : {row.report_available}")
            print(f"  error_message    : {row.error_message or 'None'}")

            # Payload
            print(f"\n  ── PAYLOAD ({'present' if row.payload_json else 'NULL'}) ──────────────────────────────")
            if row.payload_json:
                try:
                    p = json.loads(row.payload_json)
                    # Truncate document content for readability
                    if "payload" in p and "document" in p["payload"]:
                        doc = p["payload"]["document"]
                        p["payload"]["document"] = doc[:100] + "…" if len(doc) > 100 else doc
                    print(json.dumps(p, indent=2)[:600])
                except Exception as e:
                    print(f"  PARSE ERROR: {e}")

            # Executor
            print(f"\n  ── EXECUTOR ({'present' if row.executor_output_json else 'NULL'}) ────────────────────────────")
            print(j(row.executor_output_json))

            # Review
            print(f"\n  ── REVIEW ({'present' if row.review_result_json else 'NULL'}) ──────────────────────────────")
            print(j(row.review_result_json))

            # Vertex
            print(f"\n  ── VERTEX PROOF ({'present' if row.vertex_event_hash else 'NULL'}) ─────────────────────────")
            if row.vertex_event_hash:
                print(f"  event_hash   : {row.vertex_event_hash}")
                print(f"  round        : {row.vertex_round}")
                print(f"  finalised_at : {row.vertex_finalised_at}")
            else:
                print("  Not yet finalised")

            # Report
            rrows = (await s.execute(text("""
                SELECT id, generated_at, generator_model,
                       narrative, eu_ai_act_json, vertex_event_hash
                FROM reports WHERE task_id = :tid
                ORDER BY generated_at DESC LIMIT 1
            """), {"tid": str(row.id)})).fetchall()

            print(f"\n  ── REPORT ({'present' if rrows else 'NULL'}) ────────────────────────────────────────")
            if rrows:
                r = rrows[0]
                print(f"  report_id      : {r.id}")
                print(f"  generated_at   : {r.generated_at}")
                print(f"  generator_model: {r.generator_model}")
                print(f"  vertex_hash    : {r.vertex_event_hash}")
                if r.narrative:
                    print(f"  narrative      : {r.narrative[:200]}…")
                if r.eu_ai_act_json:
                    try:
                        eu = json.loads(r.eu_ai_act_json)
                        articles = eu if isinstance(eu, list) else eu.get("articles", eu.get("eu_ai_act_compliance", []))
                        print(f"  EU AI Act articles: {len(articles)}")
                        for a in articles[:3]:
                            print(f"    {a.get('article','?')} — {a.get('title','?')} — {a.get('status','?')}")
                    except Exception as e:
                        print(f"  eu_ai_act parse error: {e}")
            else:
                print("  No report generated yet")

        print()
        print(SEP)
        print(f"  Total tasks shown: {len(rows)}")
        print(SEP)

    await engine.dispose()

if __name__ == "__main__":
    tid = sys.argv[1] if len(sys.argv) > 1 else None
    asyncio.run(run(tid))
