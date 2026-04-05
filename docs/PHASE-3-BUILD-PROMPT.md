# Auditex -- Phase 3 Build Prompt
# Celery Workers + Claude Execution Layer
# Paste this entire file into a new Claude session to continue the build.

---

## PRODUCT: Auditex -- AI Workflow Compliance Platform
## SESSION: Phase 3 -- Celery Workers + Claude Execution Layer

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

  powershell -ExecutionPolicy Bypass -File run.ps1 -cmd "command here"

Claude reads logs from runs\ directly via filesystem MCP.

---

## WHAT IS COMPLETE

### Phase 0 -- Scaffold (commit e37b9f8)
- Git repo, folder scaffold, docker-compose, Makefile, run.ps1

### Phase 1 -- Database Models (commit c4dd0fb)
- ORM models: Agent, Task, AuditEvent, Report
- Alembic migration 0001_initial_schema
- audit_events: RLS + triggers blocking UPDATE and DELETE
- MT-006 PASSED: tamper-proof verified

### Phase 2 -- API Routes + Task Submission (commit c4dd0fb)
Files written:
- backend/app/api/v1/health.py      -- GET /api/v1/health, GET /api/v1/health/deep
- backend/app/api/v1/tasks.py       -- POST /api/v1/tasks, GET /api/v1/tasks/{id}, GET /api/v1/tasks
- backend/app/api/v1/agents.py      -- POST/GET /api/v1/agents
- backend/app/api/middleware/auth.py -- X-API-Key Redis-backed validation
- backend/app/models/task.py        -- TaskCreate, TaskResponse, TaskStatus (Pydantic)
- backend/app/models/agent.py       -- AgentCreate, AgentResponse (Pydantic)
- backend/db/repositories/task_repo.py
- backend/db/repositories/agent_repo.py
- backend/db/repositories/event_repo.py  -- INSERT only
- backend/app/main.py               -- all routers registered
- backend/scripts/seed_test_data.py -- creates test API key + system agent

MT-001 PASSED: health deep check -- all 4 tables, DB + Redis connected
MT-002 PASSED: POST /api/v1/tasks returns {"task_id":"<uuid>","status":"QUEUED",...}
MT-003 PASSED: GET /api/v1/tasks/{id} returns full task detail with null executor/review/vertex

Test API key: auditex-test-key-phase2
System agent UUID: ede4995c-4129-4066-8d96-fa8e246a4a10

---

## PHASE 3 GOAL: Celery Workers + Claude Execution Layer

By end of Phase 3, MT-004 must pass:
- Submit a task via POST /api/v1/tasks
- Task automatically progresses: QUEUED -> EXECUTING -> COMPLETED (Phase 3 skips REVIEWING/FINALISING -- those are Phase 4)
- GET /api/v1/tasks/{id} returns status=COMPLETED with executor fields populated
- executor.model = "claude-sonnet-4-6"
- executor.output is a structured JSON object (task-specific)
- executor.confidence is a float 0.0-1.0

### Files to create:

1. backend/workers/celery_app.py
   - Celery app factory
   - Queue definitions: execution_queue, review_queue, reporting_queue, dlq
   - Redis as broker and result backend

2. backend/workers/execution_worker.py
   - execute_task Celery task
   - Reads task from DB, calls claude_executor, updates task status
   - On success: status -> COMPLETED (Phase 3 -- review layer added in Phase 4)
   - On failure after 3 retries: status -> FAILED, route to DLQ

3. backend/services/claude_service.py
   - Thin wrapper around Anthropic SDK
   - Handles: API key from settings, retry on rate limit (429), timeout (30s)
   - Returns raw message object
   - Logs token usage per call

4. backend/core/execution/claude_executor.py
   - Builds system prompt based on task_type
   - Calls claude_service
   - Parses and validates structured JSON output against task schema
   - Returns ExecutorResult: {output: dict, confidence: float, reasoning: str, model: str, tokens_used: int}

5. backend/core/execution/retry_handler.py
   - exponential_backoff(): 1s, 2s, 4s -- max 3 attempts
   - route_to_dlq(): marks task FAILED, inserts audit event
   - Handles: API timeout, rate limit (429), invalid JSON output

6. backend/core/execution/task_schemas.py
   - Per-task-type output schemas (Pydantic models)
   - DocumentReviewOutput: {completeness: float, missing_fields: list, recommendation: str, reasoning: str, confidence: float}
   - GenericTaskOutput: {result: str, reasoning: str, confidence: float}

7. backend/app/api/v1/tasks.py -- UPDATE (add Celery task dispatch on submit)
   - After create_task(), call execute_task.delay(str(task.id))
   - No other changes

8. Manual test scripts:
   - docs/testing/manual-test-scripts/MT-004-execution-complete.ps1
     - Submit task, poll every 5s until COMPLETED or FAILED (max 60s)
     - Validate: status=COMPLETED, executor.model present, executor.confidence is float

### IMPORTANT: docker-compose.yml celery-worker command
The celery-worker service command must be:
  celery -A workers.celery_app worker --loglevel=info -Q execution_queue,review_queue,reporting_queue,dlq

### IMPORTANT: ANTHROPIC_API_KEY
The .env file has ANTHROPIC_API_KEY=placeholder.
For Phase 3 to actually call Claude, a real key is needed.
Before running MT-004, instruct the user to:
  1. Add their real ANTHROPIC_API_KEY to the .env file
  2. Run: docker compose up -d (to reload env -- no rebuild needed with volume mount)
  3. Restart celery worker: docker compose restart celery-worker

### Task type system prompts (use these exactly):

document_review:
  "You are an expert document review specialist for a financial compliance team.
   You are reviewing a document for completeness and accuracy.
   You must respond with ONLY a valid JSON object matching this exact schema:
   {
     \"completeness\": <float 0.0-1.0>,
     \"missing_fields\": [<string>, ...],
     \"recommendation\": \"APPROVE\" | \"REQUEST_ADDITIONAL_INFO\" | \"REJECT\",
     \"reasoning\": \"<2-3 sentence explanation>\",
     \"confidence\": <float 0.0-1.0>
   }
   Do not include any text outside the JSON object."

generic (fallback for unknown task_type):
  "You are an AI task execution specialist for a compliance platform.
   Complete the following task and respond with ONLY a valid JSON object:
   {
     \"result\": \"<your output>\",
     \"reasoning\": \"<2-3 sentence explanation>\",
     \"confidence\": <float 0.0-1.0>
   }
   Do not include any text outside the JSON object."

---

## MANUAL TEST MT-004

### MT-004: Task Execution Complete
  PRECONDITIONS:
    - Real ANTHROPIC_API_KEY in .env
    - celery-worker restarted after key added
    - MT-002 test key active (auditex-test-key-phase2)
  INPUT: POST /api/v1/tasks (same body as MT-002)
  POLL: GET /api/v1/tasks/{task_id} every 5 seconds, max 60 seconds
  EXPECTED FINAL RESPONSE:
  {
    "task_id": "<uuid>",
    "status": "COMPLETED",
    "task_type": "document_review",
    "workflow_id": "test-wf-001",
    "created_at": "<timestamp>",
    "executor": {
      "model": "claude-sonnet-4-6",
      "output": {
        "completeness": <float>,
        "missing_fields": [...],
        "recommendation": "APPROVE" | "REQUEST_ADDITIONAL_INFO" | "REJECT",
        "reasoning": "<string>",
        "confidence": <float>
      },
      "confidence": <float>,
      "completed_at": "<timestamp>"
    },
    "review": null,
    "vertex": null,
    "report_available": false
  }

---

## START INSTRUCTIONS FOR NEW SESSION

1. Read this prompt fully.
2. Read spec: C:\Users\v_sen\Documents\Projects\0001_Hack0014_Vertex_Swarm_Tashi\doc\POC-ENGINE-PRODUCT-SPEC-v1.md
3. Check git: powershell -ExecutionPolicy Bypass -File run.ps1 -cmd "git log --oneline -5"
4. Read existing files before modifying them (especially tasks.py -- needs Celery dispatch added)
5. Write all Phase 3 files via filesystem MCP directly.
6. Update docker-compose.yml celery-worker command to include all queues.
7. Instruct user to add real ANTHROPIC_API_KEY, restart celery-worker.
8. Run MT-004. Read log from runs\ directly.
9. Commit: "feat: Phase 3 complete -- Celery execution Claude executor MT-004 PASS"

DO NOT proceed to Phase 4 until MT-004 passes.
Phase 4: Review layer + GPT-4o reviewer + hash commitment scheme (D-06).
Phase 5: Vertex consensus integration.
Phase 6: Reporting layer + EU AI Act export.
