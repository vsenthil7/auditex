"""
Auditex -- Backend Data Verification Script
Verifies what data the API actually stores and returns for tasks.

Run:
  powershell -ExecutionPolicy Bypass -File run.ps1 -cmd "docker compose exec api python scripts/verify_task_data.py"

Or pass a specific task_id:
  powershell -ExecutionPolicy Bypass -File run.ps1 -cmd "docker compose exec api python scripts/verify_task_data.py <task_id>"
"""
from __future__ import annotations

import asyncio
import json
import sys
from datetime import timezone

from db.connection import get_engine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

SEP = "─" * 70

def fmt(val):
    if val is None:
        return "NULL"
    if isinstance(val, str) and len(val) > 200:
        return val[:200] + "…"
    return str(val)

async def run(task_id: str | None = None):
    engine = get_engine()
    async with AsyncSession(engine) as session:

        if task_id:
            query = text("""
                SELECT id, task_type, status, created_at, updated_at,
                       payload_json, executor_output_json, review_result_json,
                       vertex_event_hash, vertex_round, vertex_finalised_at,
                       report_available, error_message
                FROM tasks
                WHERE id = :tid
            """)
            rows = (await session.execute(query, {"tid": task_id})).fetchall()
        else:
            query = text("""
                SELECT id, task_type, status, created_at, updated_at,
                       payload_json, executor_output_json, review_result_json,
                       vertex_event_hash, vertex_round, vertex_finalised_at,
                       report_available, error_message
                FROM tasks
                ORDER BY created_at DESC
                LIMIT 5
            """)
            rows = (await session.execute(query)).fetchall()

        if not rows:
            print("No tasks found.")
            return

        for row in rows:
            print()
            print(SEP)
            print(f"  TASK  {row.id}")
            print(SEP)
            print(f"  type            : {row.task_type}")
            print(f"  status          : {row.status}")
            print(f"  created_at      : {row.created_at}")
            print(f"  updated_at      : {row.updated_at}")
            print(f"  report_available: {row.report_available}")
            print(f"  error_message   : {fmt(row.error_message)}")
            print()

            # Payload
            print("  ── PAYLOAD ──────────────────────────────────────────────")
            if row.payload_json:
                try:
                    payload = json.loads(row.payload_json)
                    # Show document truncated
                    if "payload" in payload and "document" in payload["payload"]:
                        doc = payload["payload"]["document"]
                        payload["payload"]["document"] = doc[:120] + "…" if len(doc) > 120 else doc
                    print(json.dumps(payload, indent=4)[:800])
                except Exception as e:
                    print(f"  parse error: {e}")
                    print(f"  raw: {fmt(row.payload_json)}")
            else:
                print("  NULL")

            # Executor output
            print()
            print("  ── EXECUTOR OUTPUT ──────────────────────────────────────")
            if row.executor_output_json:
                try:
                    print(json.dumps(json.loads(row.executor_output_json), indent=4)[:800])
                except Exception as e:
                    print(f"  parse error: {e}")
                    print(f"  raw: {fmt(row.executor_output_json)}")
            else:
                print("  NULL (task not yet executed)")

            # Review result
            print()
            print("  ── REVIEW RESULT ────────────────────────────────────────")
            if row.review_result_json:
                try:
                    review = json.loads(row.review_result_json)
                    # Truncate long fields
                    print(json.dumps(review, indent=4)[:1000])
                except Exception as e:
                    print(f"  parse error: {e}")
                    print(f"  raw: {fmt(row.review_result_json)}")
            else:
                print("  NULL (review not yet complete)")

            # Vertex proof
            print()
            print("  ── VERTEX PROOF ─────────────────────────────────────────")
            if row.vertex_event_hash:
                print(f"  event_hash   : {row.vertex_event_hash}")
                print(f"  round        : {row.vertex_round}")
                print(f"  finalised_at : {row.vertex_finalised_at}")
            else:
                print("  NULL (not yet finalised)")

            # Report
            print()
            print("  ── REPORT ───────────────────────────────────────────────")
            report_query = text("""
                SELECT id, generated_at, report_json
                FROM reports
                WHERE task_id = :tid
                ORDER BY generated_at DESC
                LIMIT 1
            """)
            report_rows = (await session.execute(report_query, {"tid": str(row.id)})).fetchall()
            if report_rows:
                r = report_rows[0]
                print(f"  report_id    : {r.id}")
                print(f"  generated_at : {r.generated_at}")
                if r.report_json:
                    try:
                        rdata = json.loads(r.report_json)
                        summary = rdata.get("plain_english_summary", "")
                        print(f"  summary      : {summary[:200]}…")
                        articles = rdata.get("eu_ai_act_compliance", [])
                        print(f"  articles     : {len(articles)}")
                        for a in articles:
                            print(f"    {a.get('article')} — {a.get('title')} — {a.get('status')}")
                    except Exception as e:
                        print(f"  parse error: {e}")
            else:
                print("  No report generated yet")

        print()
        print(SEP)
        print(f"  Verified {len(rows)} task(s)")
        print(SEP)

    await engine.dispose()

if __name__ == "__main__":
    task_id = sys.argv[1] if len(sys.argv) > 1 else None
    asyncio.run(run(task_id))
