# AUDITEX PROJECT STATUS
# Updated: 2026-04-06 16:48
# Rules: update this file at end of every work block
# NEVER compact chat without asking. Warn at 60% context.

## PROJECT
- Root: C:\Users\v_sen\Documents\Projects\0001_Hack0014_Vertex_Swarm_Tashi\auditex
- Stack: FastAPI + Celery + PostgreSQL + Redis + React/TS + Playwright in Docker
- Ops: ops.ps1 — actions: git, playwright, status, clear, celery-logs, diag, docker-ps
- Logs: runs/ops_<action>_<timestamp>.log — read directly, never paste

## CURRENT STATUS: 11/11 tests PASSING (last run: ops_playwright_20260406_131903.log)
## WARNING: reporting_worker fix not yet verified — needs celery rebuild + playwright run

## TEST MATRIX
| TC | Test | Result |
|----|------|--------|
| TC-01 | Dashboard loads | PASS |
| TC-02 | document_review APPROVE | PASS |
| TC-03 | document_review NOT APPROVE boundary | PASS |
| TC-04 | document_review REJECT | PASS |
| TC-05 | risk_analysis APPROVE | PASS |
| TC-06 | risk_analysis REQUEST_ADDITIONAL_INFO | PASS |
| TC-07 | risk_analysis REJECT | PASS |
| TC-08 | contract_check NOT REJECT boundary | PASS |
| TC-09 | contract_check REQUEST_AMENDMENTS | PASS |
| TC-10 | contract_check REJECT | PASS |
| TC-11 | UI consistency 9 tasks 5 steps green lifecycle | PASS |

## TASK TYPE MATRIX
| Type | Recommendations | Extra |
|------|----------------|-------|
| document_review | APPROVE / REQUEST_ADDITIONAL_INFO / REJECT | completeness 0-1 |
| risk_analysis | APPROVE / REQUEST_ADDITIONAL_INFO / REJECT | risk_level LOW/MEDIUM/HIGH |
| contract_check | APPROVE / REQUEST_AMENDMENTS / REJECT | compliance_status COMPLIANT/PARTIAL/NON_COMPLIANT |

Pipeline: QUEUED > EXECUTING > REVIEWING > FINALISING > COMPLETED | FAILED | ESCALATED

## KEY FILES
- backend/workers/execution_worker.py — fresh engine+session+loop per task
- backend/workers/reporting_worker.py — FIXED asyncio loop bug (fresh engine+loop)
- backend/core/execution/claude_executor.py — max_tokens=2048
- backend/core/execution/task_schemas.py — 3 schemas
- backend/app/api/v1/tasks.py — list basic / detail full
- backend/db/models/base.py — TimestampMixin has only created_at NO updated_at
- frontend/src/store/taskStore.ts — selectTask fetches immediately, refreshes 3s
- frontend/src/services/api.ts — transforms eu_ai_act flat dict to array
- frontend/src/components/TaskDetail.tsx — 5 collapsible steps, lifecycle dots
- frontend/tests/dashboard.spec.ts — 11 tests 3x3 matrix + dashboard + UI

## DB QUEUE FIX
docker compose exec postgres psql -U auditex -d auditex -c "UPDATE tasks SET status='FAILED', failure_reason='Force-failed' WHERE status IN ('QUEUED','EXECUTING','REVIEWING','FINALISING') AND created_at < NOW() - INTERVAL '5 minutes'"
Columns: status, failure_reason, created_at — NO updated_at NO error_message

## API CONTRACT
- GET /api/v1/tasks — basic list
- GET /api/v1/tasks/{id} — full detail
- GET /api/v1/reports/{task_id} — report + eu_ai_act
- GET /api/v1/reports/{task_id}/export — flat article keys

## BOUNDARY TEST LOGIC
- TC-03: asserts NOT APPROVE (REJECT or REQUEST_ADDITIONAL_INFO both valid)
- TC-08: asserts NOT REJECT (APPROVE or REQUEST_AMENDMENTS both valid)

## GIT LOG
- 78603b5 feat: ops.ps1 Do-Git diff+Y/N gate; claude-memory store; restore .gitignore
- 0309a08 fix: reporting_worker asyncio loop bug; rename MEMORY.md to PROJECT_STATUS.md

## MEMORY FILES
- Claude rules: C:\Users\v_sen\Documents\Projects\claude-memory\global\CLAUDE_RULES.md
- Memory backup: C:\Users\v_sen\Documents\Projects\claude-memory\global\MEMORY_BACKUP.md
- This file backup: C:\Users\v_sen\Documents\Projects\claude-memory\projects\auditex\PROJECT_STATUS.md
