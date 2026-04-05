# Auditex -- Phase 2 Build Prompt
# API Routes + Task Submission
# Paste this entire file into a new Claude session to continue the build.

---

## PRODUCT: Auditex -- AI Workflow Compliance Platform
## SESSION: Phase 2 -- API Routes + Task Submission

---

## ANTI-DRIFT RULES (non-negotiable, read first)

1. Git first. Check git status before writing any code.
2. Manual test before automation. Write MT-XXX script, human runs it, Claude validates, then unit tests.
3. One step at a time. Wait for confirmation before next step.
4. No scope shrink without written justification.
5. No hallucinated libraries. Every package must be real and versioned.
6. Claude as reporter, Vertex as decider. LLM never in real-time control loop.
7. Multi-model for review. Claude executes, GPT-4o reviews. Never self-judge.
8. Enterprise standard. No hacks. No shortcuts.
9. Check before assuming. Read run logs via filesystem MCP before responding.
10. Diagram numbers are permanent. D-01 through D-06 never change.

---

## ENVIRONMENT

- Windows, user v_sen, host SENBHU
- Project root: C:\Users\v_sen\Documents\Projects\0001_Hack0014_Vertex_Swarm_Tashi\auditex
- Spec file: C:\Users\v_sen\Documents\Projects\0001_Hack0014_Vertex_Swarm_Tashi\doc\POC-ENGINE-PRODUCT-SPEC-v1.md
- Git branch: main
- Docker: running (api, postgres, redis, foxmq, celery-worker)
- API: http://localhost:8000
- MCP: filesystem read/write active. Shell MCP not available.
- Run logs: project root\runs\ -- Claude reads these directly, no copy-paste needed.

## HOW TO RUN COMMANDS

All commands use run.ps1 with logging:
  powershell -ExecutionPolicy Bypass -File run.ps1 -cmd "command here"
  powershell -ExecutionPolicy Bypass -File run.ps1 -cmd "cmd1" -cmd2 "cmd2" -cmd3 "cmd3"

Claude reads logs from runs\ directly via filesystem MCP.

---

## WHAT IS COMPLETE (Phases 0 and 1)

### Phase 0 -- Scaffold (commits e37b9f8, f1099e8)
- Git repo on main branch
- Full folder scaffold per spec S03
- .gitignore, .env.example, .env (dev placeholders)
- docker-compose.yml: api, celery-worker, postgres:16, redis:7, foxmq (mosquitto)
- Makefile, run.ps1 (log system), commit.ps1
- MT-000 PASSED: stack boots, health endpoint returns 200

### Phase 1 -- Database Models
Files written:
- backend/db/models/base.py        -- DeclarativeBase, TimestampMixin, UUIDPrimaryKeyMixin
- backend/db/models/agent.py       -- Agent ORM model
- backend/db/models/task.py        -- Task ORM model (full lifecycle states)
- backend/db/models/audit_event.py -- AuditEvent (append-only, tamper-proof)
- backend/db/models/report.py      -- Report (PoC report, signed)
- backend/db/models/__init__.py    -- exports all models for Alembic
- backend/db/connection.py         -- async SQLAlchemy engine + session factory
- backend/app/config.py            -- pydantic-settings (reads .env)
- backend/app/main.py              -- FastAPI app with real health check
- backend/alembic.ini
- backend/db/migrations/env.py
- backend/db/migrations/versions/0001_initial_schema.py
  -- Creates: agents, tasks, audit_events, reports
  -- CRITICAL: audit_events has RLS + triggers blocking UPDATE and DELETE

MT-006 PASSED (all 4 steps):
- INSERT: PASS
- UPDATE blocked: PASS ("audit_events is append-only -- UPDATE is not permitted")
- DELETE blocked: PASS ("audit_events is append-only -- DELETE is not permitted")
- Record intact: PASS

Health check:
  {"status":"healthy","version":"0.1.0","services":{"database":"connected","redis":"connected","vertex":"not_connected"}}

---

## PHASE 2 GOAL: API Routes + Task Submission

By end of Phase 2, MT-001, MT-002, MT-003 from spec S07 must pass.

### Files to create:

1. backend/app/api/v1/health.py
   - GET /api/v1/health
   - GET /api/v1/health/deep

2. backend/app/models/task.py  (Pydantic schemas -- NOT the ORM model)
   - TaskCreate, TaskResponse, TaskStatus enum

3. backend/app/models/agent.py  (Pydantic schemas)
   - AgentCreate, AgentResponse

4. backend/app/api/v1/tasks.py
   - POST /api/v1/tasks       -- submit task (MT-002)
   - GET  /api/v1/tasks/{id}  -- poll status (MT-003)
   - GET  /api/v1/tasks       -- list tasks paginated

5. backend/app/api/v1/agents.py
   - POST /api/v1/agents
   - GET  /api/v1/agents
   - GET  /api/v1/agents/{agent_id}

6. backend/app/api/middleware/auth.py
   - X-API-Key header validation (Redis-backed for Phase 2)

7. backend/db/repositories/task_repo.py
   - create_task(), get_task(), list_tasks(), update_task_status()

8. backend/db/repositories/agent_repo.py
   - create_agent(), get_agent(), list_agents()

9. backend/db/repositories/event_repo.py
   - insert_event() -- INSERT only, no update/delete methods ever

10. backend/app/main.py  -- register all routers

11. scripts/setup/seed_test_data.py
    - Creates test API key in Redis: auditex-test-key-phase2
    - Creates system agent in DB

12. Manual test scripts:
    - docs/testing/manual-test-scripts/MT-001-health-deep.ps1
    - docs/testing/manual-test-scripts/MT-002-submit-task.ps1
    - docs/testing/manual-test-scripts/MT-003-poll-status.ps1

---

## MANUAL TESTS (spec S07 format)

### MT-001: Health Deep Check
  INPUT: GET /api/v1/health/deep  X-API-Key: auditex-test-key-phase2
  EXPECTED:
  {
    "status": "healthy",
    "version": "0.1.0",
    "services": {
      "database": "connected",
      "redis": "connected",
      "foxmq": "connected",
      "vertex": "not_connected"
    },
    "database_tables": ["agents","tasks","audit_events","reports"]
  }

### MT-002: Submit Task
  INPUT: POST /api/v1/tasks  X-API-Key: auditex-test-key-phase2
  BODY:
  {
    "task_type": "document_review",
    "payload": {
      "document": "Test loan application. Applicant: John Smith. Income: 50000.",
      "review_criteria": ["completeness","income_verification"]
    },
    "metadata": {"submitted_by":"test_client","workflow_id":"test-wf-001"}
  }
  EXPECTED: {"task_id":"<uuid>","status":"QUEUED","created_at":"<timestamp>"}

### MT-003: Poll Task Status
  INPUT: GET /api/v1/tasks/{task_id}  X-API-Key: auditex-test-key-phase2
  EXPECTED:
  {
    "task_id": "<uuid>",
    "status": "QUEUED",
    "task_type": "document_review",
    "workflow_id": "test-wf-001",
    "created_at": "<timestamp>",
    "executor": null,
    "review": null,
    "vertex": null,
    "report_available": false
  }

---

## START INSTRUCTIONS FOR NEW SESSION

1. Read this prompt fully.
2. Read spec: C:\Users\v_sen\Documents\Projects\0001_Hack0014_Vertex_Swarm_Tashi\doc\POC-ENGINE-PRODUCT-SPEC-v1.md
3. Check git:
   powershell -ExecutionPolicy Bypass -File run.ps1 -cmd "git log --oneline" -cmd2 "git status"
4. If Phase 1 not committed yet:
   powershell -ExecutionPolicy Bypass -File run.ps1 -cmd "git add -A" -cmd2 "git commit -m 'feat: Phase 1 complete -- DB models migrations tamper-proof MT-006 PASS'"
5. Write all Phase 2 files via filesystem MCP directly. Do not ask user to create files.
6. Rebuild: powershell -ExecutionPolicy Bypass -File run.ps1 -cmd "docker compose up -d --build"
7. Run seed script inside container to create test API key.
8. Run MT-001, MT-002, MT-003 in order. Read logs from runs\ directly.
9. Commit: "feat: Phase 2 complete -- API routes task submission MT-001 MT-002 MT-003 PASS"

DO NOT proceed to Phase 3 until all three manual tests pass.
Phase 3: Celery workers + Claude execution layer.
Phase 4: Review layer + hash commitment scheme (D-06).
Phase 5: Vertex consensus integration.
Phase 6: Reporting layer + EU AI Act export.
