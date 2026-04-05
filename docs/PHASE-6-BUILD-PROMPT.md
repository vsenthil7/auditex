# Auditex -- Phase 6 Build Prompt
# Reporting Layer (PoC Report + EU AI Act Export)
# Paste this entire file into a new Claude session to continue the build.

---

## PRODUCT: Auditex -- AI Workflow Compliance Platform
## SESSION: Phase 6 -- Reporting Layer

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
- Docker: running (api, postgres, redis, celery-worker)
- API: http://localhost:8000
- MCP: filesystem read/write active. Shell MCP not available.
- Run logs: project root\runs\ -- Claude reads these directly, no copy-paste needed.

## HOW TO RUN COMMANDS

  powershell -ExecutionPolicy Bypass -File run.ps1 -cmd "command here"

For git commits:
  powershell -ExecutionPolicy Bypass -File run.ps1 -cmd "git add -A"
  git commit -m "message"

---

## WHAT IS COMPLETE

### Phase 0 -- Scaffold (commit e37b9f8)
- Git repo, folder scaffold, docker-compose, Makefile, run.ps1

### Phase 1 -- Database Models (commit c4dd0fb)
- ORM models: Agent, Task, AuditEvent, Report
- Alembic migration 0001_initial_schema
- audit_events: RLS + triggers blocking UPDATE and DELETE
- MT-006 (tamper-proof) PASSED

### Phase 2 -- API Routes + Task Submission (commit c4dd0fb)
- backend/app/api/v1/health.py      -- GET /api/v1/health, GET /api/v1/health/deep
- backend/app/api/v1/tasks.py       -- POST /api/v1/tasks, GET /api/v1/tasks/{id}, GET /api/v1/tasks
- backend/app/api/v1/agents.py      -- POST/GET /api/v1/agents
- backend/app/api/middleware/auth.py -- X-API-Key Redis-backed validation
- MT-001, MT-002, MT-003 PASSED

### Phase 3 -- Celery Workers + Claude Execution Layer (commit 70023b1)
- backend/workers/celery_app.py
- backend/workers/execution_worker.py
- backend/services/claude_service.py
- backend/core/execution/claude_executor.py
- backend/core/execution/task_schemas.py
- backend/core/execution/retry_handler.py
- MT-004 PASSED

### Phase 4 -- Review Layer + GPT-4o + Hash Commitment (commit a5be5a9)
- backend/services/openai_service.py
- backend/core/review/hash_commitment.py
- backend/core/review/gpt4o_reviewer.py
- backend/core/review/coordinator.py
- backend/core/review/consensus_eval.py
- backend/workers/execution_worker.py  (updated)
- backend/app/api/v1/tasks.py          (updated)
- MT-005 PASSED: 25/25 checks

### Phase 5 -- Vertex Consensus Layer (commit 6585523)
- backend/core/consensus/event_builder.py
- backend/core/consensus/foxmq_client.py   (stub)
- backend/core/consensus/vertex_client.py  (stub, real SHA-256 + Redis round)
- backend/workers/execution_worker.py      (updated: FINALISING status)
- backend/app/api/v1/tasks.py              (updated: vertex.finalised_at)
- MT-006 PASSED: 14/14 checks
  Status lifecycle: QUEUED -> EXECUTING -> REVIEWING -> FINALISING -> COMPLETED
  vertex.event_hash = real SHA-256, vertex.round = Redis INCR, vertex.finalised_at = UTC ISO

Test API key: auditex-test-key-phase2
System agent UUID: ede4995c-4129-4066-8d96-fa8e246a4a10

---

## PHASE 6 GOAL: Reporting Layer

By end of Phase 6, MT-007 must pass:
- Submit a task via POST /api/v1/tasks
- Task completes: QUEUED -> EXECUTING -> REVIEWING -> FINALISING -> COMPLETED
- GET /api/v1/tasks/{id} returns report_available=true
- GET /api/v1/reports/{task_id} returns a full PoC report with:
  - plain_english_summary: non-empty string (Claude-generated narrative)
  - eu_ai_act: object with article_9, article_13, article_17 fields
  - vertex_proof: object with event_hash, round, finalised_at
  - schema_version: "poc_report_v1"
  - generated_at: ISO timestamp
- GET /api/v1/reports/{task_id}/export?format=eu_ai_act returns a structured JSON export

### Report generation flow

After COMPLETED status is set in execution_worker.py:
  a. Dispatch a Celery reporting task: generate_poc_report.delay(task_id_str)
  b. Reporting worker reads the completed task from DB
  c. Calls Claude API to generate a plain-English narrative
  d. EU AI Act formatter maps fields to Article 9/13/17 structure
  e. Writes Report record to DB (report table)
  f. Updates task: report_available=True (add this boolean column if not present)

### Files to create

1. backend/core/reporting/poc_generator.py
   - generate_report(task_id) -> PoCReportData
   - Reads completed task from DB (executor_output, review_result, vertex fields)
   - Calls Claude API with a grounded system prompt:
     "You are a compliance documentation specialist. Generate a plain-English
      narrative from the event log below. Do not add information not present.
      Write in formal English suitable for regulatory submission."
   - Returns PoCReportData dataclass:
     {task_id, plain_english_summary, generated_at}

2. backend/core/reporting/eu_act_formatter.py
   - format_eu_ai_act(task, executor_output, review_result, vertex) -> dict
   - Maps fields to EU AI Act Article 9/13/17 structure:
     {
       "article_9_risk_management": {
         "task_type": str,
         "executor_model": str,
         "confidence_score": float,
         "risk_assessment": "LOW|MEDIUM|HIGH"
       },
       "article_13_transparency": {
         "decision_made": str,
         "reasoning_summary": str,
         "reviewers": [{"model", "verdict", "confidence"}],
         "consensus": str
       },
       "article_17_quality_management": {
         "all_commitments_verified": bool,
         "vertex_event_hash": str,
         "vertex_round": int,
         "finalised_at": str,
         "audit_trail_available": true
       }
     }

3. backend/core/reporting/__init__.py
   - Empty (verify before creating)

4. backend/workers/reporting_worker.py
   - generate_poc_report Celery task
   - Queue: reporting_queue
   - Reads task from DB, calls poc_generator + eu_act_formatter
   - Writes Report ORM record
   - Updates task.report_available = True (via task_repo)

5. backend/workers/execution_worker.py -- UPDATE
   - After step 11 (COMPLETED), dispatch reporting task:
     from workers.reporting_worker import generate_poc_report as celery_report_task
     celery_report_task.delay(task_id_str)

6. backend/app/api/v1/reports.py -- NEW
   - GET /api/v1/reports/{task_id}
     Returns full PoC report: plain_english_summary, eu_ai_act, vertex_proof,
     schema_version, generated_at
   - GET /api/v1/reports/{task_id}/export?format=eu_ai_act
     Returns eu_ai_act dict + plain_english_summary + vertex_proof + schema_version

7. backend/app/api/v1/tasks.py -- UPDATE
   - report_available: deserialise from task.report_available boolean field
   - Currently hardcoded False -- make it real

8. backend/app/main.py -- UPDATE
   - Register reports router

9. backend/db/models/task.py -- UPDATE (if report_available column missing)
   - Add: report_available: Mapped[bool] = mapped_column(Boolean, default=False)

10. Alembic migration -- if schema changes needed
    - Add report_available column to tasks table if not present

11. Manual test script:
    - docs/testing/manual-test-scripts/MT-007-reporting.ps1
      - Submit task, poll until COMPLETED
      - Poll GET /api/v1/tasks/{id} until report_available=true (max 60s extra)
      - GET /api/v1/reports/{task_id}
      - Validate: plain_english_summary non-empty string
      - Validate: eu_ai_act has article_9, article_13, article_17 keys
      - Validate: vertex_proof.event_hash is 64-char hex
      - Validate: schema_version = "poc_report_v1"
      - GET /api/v1/reports/{task_id}/export?format=eu_ai_act
      - Validate: export has article_9_risk_management, article_13_transparency,
                  article_17_quality_management, plain_english_summary, schema_version

### MT-007 expected report response shape:
{
  "task_id": "<uuid>",
  "schema_version": "poc_report_v1",
  "generated_at": "<ISO timestamp>",
  "plain_english_summary": "<non-empty string, Claude-generated>",
  "eu_ai_act": {
    "article_9_risk_management": {
      "task_type": "document_review",
      "executor_model": "claude-sonnet-4-6",
      "confidence_score": <float>,
      "risk_assessment": "LOW|MEDIUM|HIGH"
    },
    "article_13_transparency": {
      "decision_made": "<recommendation from executor output>",
      "reasoning_summary": "<brief summary>",
      "reviewers": [{"model": str, "verdict": str, "confidence": float}],
      "consensus": "3_OF_3_APPROVE"
    },
    "article_17_quality_management": {
      "all_commitments_verified": true,
      "vertex_event_hash": "<64-char hex>",
      "vertex_round": <int>,
      "finalised_at": "<ISO timestamp>",
      "audit_trail_available": true
    }
  },
  "vertex_proof": {
    "event_hash": "<64-char hex>",
    "round": <int>,
    "finalised_at": "<ISO timestamp>"
  },
  "report_available": true
}

---

## MANUAL TEST MT-007

### MT-007: PoC Report Generation + EU AI Act Export
  PRECONDITIONS:
    - Real ANTHROPIC_API_KEY in .env
    - All containers running (api, postgres, redis, celery-worker)
    - MT-006 passing (Phase 5 complete)
  INPUT: POST /api/v1/tasks (same body as MT-006)
  PASS CONDITIONS:
    - Task reaches COMPLETED
    - report_available = true (within 60s of COMPLETED)
    - GET /api/v1/reports/{task_id} returns 200
    - plain_english_summary is a non-empty string
    - eu_ai_act has article_9, article_13, article_17 keys
    - vertex_proof.event_hash is 64-char hex
    - schema_version = "poc_report_v1"
    - GET /api/v1/reports/{task_id}/export?format=eu_ai_act returns 200
    - Export has all required top-level fields

---

## START INSTRUCTIONS FOR NEW SESSION

1. Read this prompt fully.
2. Read spec: C:\Users\v_sen\Documents\Projects\0001_Hack0014_Vertex_Swarm_Tashi\doc\POC-ENGINE-PRODUCT-SPEC-v1.md
3. Check git: powershell -ExecutionPolicy Bypass -File run.ps1 -cmd "git log --oneline -5"
4. Check existing files before modifying (especially execution_worker.py, tasks.py, db/models/task.py)
5. Check backend/core/reporting/ directory -- what already exists
6. Check Report ORM model: backend/db/models/report.py
7. Check task_repo for report_available support
8. Write all Phase 6 files via filesystem MCP directly.
9. Restart celery worker after writing files.
10. Run MT-007. Read result from runs\ directly.
11. Commit: feat: Phase 6 complete -- reporting layer EU AI Act export MT-007 PASS

DO NOT proceed to Phase 7 until MT-007 passes.
Phase 7: Dashboard frontend (React) + real-time task status polling.
