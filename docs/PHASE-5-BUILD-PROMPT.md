# Auditex -- Phase 5 Build Prompt
# Vertex Consensus Layer (FoxMQ event submission + tamper-proof log)
# Paste this entire file into a new Claude session to continue the build.

---

## PRODUCT: Auditex -- AI Workflow Compliance Platform
## SESSION: Phase 5 -- Vertex Consensus Integration

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

For git commits (no && in PowerShell, double-quote issues with run.ps1):
  powershell -ExecutionPolicy Bypass -File run.ps1 -cmd "git add -A"
  git commit -m "message"   (run directly, not via run.ps1)

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
  Flow: QUEUED -> EXECUTING -> REVIEWING -> COMPLETED
  review.consensus = 3_OF_3_APPROVE
  All 3 commitment_verified = true
  Reviewers: gpt-4o-2024-08-06, gpt-4o-2024-08-06, claude-sonnet-4-6

Test API key: auditex-test-key-phase2
System agent UUID: ede4995c-4129-4066-8d96-fa8e246a4a10

---

## PHASE 5 GOAL: Vertex Consensus Layer

By end of Phase 5, MT-006 must pass:
- Submit a task via POST /api/v1/tasks
- Task automatically progresses: QUEUED -> EXECUTING -> REVIEWING -> FINALISING -> COMPLETED
- GET /api/v1/tasks/{id} returns status=COMPLETED with executor, review, AND vertex fields populated
- vertex.event_hash = a SHA-256 hex string (the hash of the full event payload)
- vertex.round = an integer (the Vertex consensus round number, starting at 1 and incrementing)
- vertex.finalised_at = ISO timestamp

### IMPORTANT: Vertex/FoxMQ is not yet deployed

The Tashi Vertex/FoxMQ infrastructure is not running in the Docker stack yet.
Phase 5 must implement the Vertex layer with a GRACEFUL STUB that:
  - Produces a real SHA-256 event_hash (hash of the actual event payload)
  - Produces a real incrementing round number (stored in Redis, starts at 1)
  - Produces a real finalised_at timestamp
  - Writes the full event to the tamper-proof audit log (audit_events table) with the Vertex proof fields populated
  - Is designed so that when real Vertex is available, only foxmq_client.py and vertex_client.py need to change
  - Does NOT require FoxMQ/Vertex infrastructure to be running

The stub must be honest -- it must be documented as a stub, must log clearly that it is
running in VERTEX_STUB mode, and must not pretend to be real Vertex consensus.

When real Vertex is available (Phase 6 or later):
  - foxmq_client.py: replace stub with real MQTT publish to FoxMQ broker
  - vertex_client.py: replace stub with real Vertex event submission and consensus polling
  - Everything else (event_builder.py, execution_worker.py, task response) stays unchanged

### New FINALISING status

Phase 5 adds a new task status between REVIEWING and COMPLETED:
  QUEUED -> EXECUTING -> REVIEWING -> FINALISING -> COMPLETED

FINALISING means: review pipeline complete, event submitted to Vertex (or stub),
waiting for consensus confirmation. In stub mode this is near-instant.

### Files to create:

1. backend/core/consensus/event_builder.py
   - build_task_completed_event(task_id, task_type, executor_output, review_result) -> dict
   - Produces the full FoxMQ/Vertex event payload:
     {
       "event_type": "task_completed",
       "task_id": "<uuid>",
       "schema_version": "1.0",
       "executor": {
         "model": "<model>",
         "output_hash": "<sha256 of json-serialised executor output>",
         "confidence": <float>
       },
       "reviewers": [
         {"model": "<model>", "verdict": "<verdict>", "committed_hash": "<hash>"},
         ...
       ],
       "consensus": "<consensus_label>",
       "all_commitments_verified": true,
       "submitted_at": "<ISO timestamp>"
     }
   - output_hash = SHA256(json.dumps(executor_output, sort_keys=True))
   - payload_hash = SHA256(json.dumps(full_payload, sort_keys=True))  stored as event_hash

2. backend/core/consensus/vertex_client.py
   - STUB ONLY for Phase 5 (clearly documented)
   - submit_event(event_payload: dict) -> VertexReceipt
   - VertexReceipt dataclass: {event_hash: str, round: int, finalised_at: str, is_stub: bool}
   - event_hash = SHA256(json.dumps(event_payload, sort_keys=True))
   - round = Redis INCR("vertex:round_counter") -- atomic increment, starts at 1
   - finalised_at = datetime.now(UTC).isoformat()
   - is_stub = True
   - Logs: "VERTEX_STUB: event finalised | hash=<16 chars>... round=<N>"
   - Designed for drop-in replacement: real implementation keeps same signature

3. backend/core/consensus/foxmq_client.py
   - STUB ONLY for Phase 5 (clearly documented)
   - publish_event(event_payload: dict) -> bool
   - In stub mode: logs "FOXMQ_STUB: event published | event_type=<type>" and returns True
   - Designed for drop-in replacement with real MQTT publish

4. backend/core/consensus/__init__.py
   - Empty (already exists -- verify before creating)

5. backend/workers/execution_worker.py -- UPDATE
   - After review pipeline completes, instead of immediately setting COMPLETED:
     a. Set status = FINALISING
     b. Call event_builder.build_task_completed_event()
     c. Call foxmq_client.publish_event() (stub: logs + returns True)
     d. Call vertex_client.submit_event() (stub: SHA256 hash + Redis round + timestamp)
     e. Store vertex receipt in task: vertex_event_hash, vertex_round, vertex_finalised_at
     f. Set status = COMPLETED
   - On consensus layer failure: log error, still complete the task (vertex fields null)
     Rationale: in stub mode, consensus failure should not block task completion.
     In production with real Vertex, this would route to DLQ.

6. backend/app/api/v1/tasks.py -- UPDATE get_task()
   - vertex field already present in response (Phase 4 scaffold, currently null)
   - Ensure vertex field returns:
     {
       "event_hash": "<sha256 hex string>",
       "round": <integer>,
       "finalised_at": "<ISO timestamp>"
     }
   - No change needed if Phase 4 already deserialises vertex_event_hash, vertex_round,
     vertex_finalised_at from the task ORM fields. Verify before modifying.

7. Manual test script:
   - docs/testing/manual-test-scripts/MT-006-vertex-consensus.ps1
     - Submit task, poll every 5s until COMPLETED or FAILED (max 120s)
     - Validate: status=COMPLETED
     - Validate: status passed through FINALISING
     - Validate: executor present (model, confidence, output, completed_at)
     - Validate: review present (consensus, 3 reviewers, all commitment_verified=true)
     - Validate: vertex present (event_hash is 64-char hex, round >= 1, finalised_at present)
     - Validate: vertex.event_hash is a valid SHA-256 hex string (64 lowercase hex chars)

### MT-006 expected final response shape:
{
  "task_id": "<uuid>",
  "status": "COMPLETED",
  "task_type": "document_review",
  "executor": {
    "model": "claude-sonnet-4-6",
    "output": { ... },
    "confidence": <float>,
    "completed_at": "<timestamp>"
  },
  "review": {
    "consensus": "3_OF_3_APPROVE",
    "reviewers": [
      {"model": "gpt-4o", "verdict": "APPROVE", "confidence": <float>, "commitment_verified": true},
      {"model": "gpt-4o", "verdict": "APPROVE", "confidence": <float>, "commitment_verified": true},
      {"model": "claude-sonnet-4-6", "verdict": "APPROVE", "confidence": <float>, "commitment_verified": true}
    ],
    "completed_at": "<timestamp>"
  },
  "vertex": {
    "event_hash": "<64-char lowercase hex SHA-256 string>",
    "round": <integer >= 1>,
    "finalised_at": "<ISO timestamp>"
  },
  "report_available": false
}

---

## MANUAL TEST MT-006

### MT-006: Vertex Consensus Complete (Stub Mode)
  PRECONDITIONS:
    - Real ANTHROPIC_API_KEY and OPENAI_API_KEY in .env
    - All containers running (api, postgres, redis, celery-worker)
    - MT-005 passing (Phase 4 complete)
    - No FoxMQ/Vertex infrastructure required (stub mode)
  INPUT: POST /api/v1/tasks (same body as MT-005)
  POLL: GET /api/v1/tasks/{task_id} every 5 seconds, max 120 seconds
  PASS CONDITIONS:
    - status = COMPLETED
    - status progression includes FINALISING
    - executor field populated
    - review.consensus = 3_OF_3_APPROVE or 2_OF_3_APPROVE
    - review.reviewers = 3 entries, all commitment_verified = true
    - vertex.event_hash = 64-char lowercase hex string
    - vertex.round >= 1
    - vertex.finalised_at = valid ISO timestamp

---

## START INSTRUCTIONS FOR NEW SESSION

1. Read this prompt fully.
2. Read spec: C:\Users\v_sen\Documents\Projects\0001_Hack0014_Vertex_Swarm_Tashi\doc\POC-ENGINE-PRODUCT-SPEC-v1.md
3. Check git: powershell -ExecutionPolicy Bypass -File run.ps1 -cmd "git log --oneline -5"
4. Read existing files before modifying (especially execution_worker.py and tasks.py)
5. Check backend/core/consensus/ directory exists and what is already in it
6. Write all Phase 5 files via filesystem MCP directly.
7. Restart celery worker after writing files.
8. Run MT-006. Read result from terminal output directly.
9. Commit: feat: Phase 5 complete -- Vertex consensus stub FINALISING status MT-006 PASS

DO NOT proceed to Phase 6 until MT-006 passes.
Phase 6: Reporting layer + EU AI Act export.
