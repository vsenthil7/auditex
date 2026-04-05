# Auditex -- Phase 4 Build Prompt
# Review Layer + GPT-4o Reviewer + Hash Commitment Scheme (D-06)
# Paste this entire file into a new Claude session to continue the build.

---

## PRODUCT: Auditex -- AI Workflow Compliance Platform
## SESSION: Phase 4 -- Review Layer + GPT-4o + Hash Commitment

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

For git commits (no && in PowerShell):
  powershell -ExecutionPolicy Bypass -File run.ps1 -cmd "git add -A"
  powershell -ExecutionPolicy Bypass -File run.ps1 -cmd "git commit -m 'message'"

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
Files written:
- backend/workers/celery_app.py          -- Celery factory, 4 queues, Redis broker
- backend/workers/execution_worker.py    -- execute_task Celery task, QUEUED->EXECUTING->COMPLETED
- backend/services/claude_service.py     -- Anthropic SDK wrapper, retry on 429/5xx/timeout
- backend/core/execution/claude_executor.py  -- prompt builder, JSON parse, Pydantic validation
- backend/core/execution/task_schemas.py     -- DocumentReviewOutput, GenericTaskOutput
- backend/core/execution/retry_handler.py    -- exponential backoff (1s/2s/4s), DLQ routing
- backend/scripts/test_api_keys.py           -- smoke test for Anthropic + OpenAI keys
- docker-compose.yml updated: PYTHONPATH=/app, ${ANTHROPIC_API_KEY}, ${OPENAI_API_KEY}
- MT-004 PASSED: QUEUED->EXECUTING->COMPLETED in 9 seconds
  executor.model = claude-sonnet-4-6
  executor.confidence = 0.88
  executor.output = full DocumentReviewOutput schema

Test API key: auditex-test-key-phase2
System agent UUID: ede4995c-4129-4066-8d96-fa8e246a4a10

---

## PHASE 4 GOAL: Review Layer + GPT-4o + Hash Commitment Scheme

By end of Phase 4, MT-005 must pass:
- Submit a task via POST /api/v1/tasks
- Task automatically progresses: QUEUED -> EXECUTING -> REVIEWING -> COMPLETED
- GET /api/v1/tasks/{id} returns status=COMPLETED with both executor AND review fields populated
- review.consensus = "3_OF_3_APPROVE" or "2_OF_3_APPROVE"
- review.reviewers = array of 3 reviewer objects, each with verdict + commitment_verified=true
- All 3 hash commitments verified (SHA256(verdict+nonce) == committed_hash)

### Files to create:

1. backend/services/openai_service.py
   - Thin wrapper around OpenAI SDK (mirrors claude_service.py pattern)
   - Reads OPENAI_API_KEY and GPT4O_MODEL from settings
   - Retry on rate limit (429), timeout 30s
   - Logs token usage per call

2. backend/core/review/hash_commitment.py
   - generate_nonce() -> str: cryptographically random 32-byte hex string
   - compute_commitment(verdict: str, nonce: str) -> str: SHA256(verdict+nonce) hex digest
   - verify_commitment(verdict: str, nonce: str, committed_hash: str) -> bool
   - Raises SecurityViolationError if verification fails

3. backend/core/review/gpt4o_reviewer.py
   - review_output(task_type, original_payload, executor_output) -> ReviewVerdict
   - ReviewVerdict dataclass: {verdict: "APPROVE"|"REJECT", reasoning: str, confidence: float, model: str}
   - System prompt: exactly as specified below
   - Calls openai_service
   - Parses and validates JSON response

4. backend/core/review/coordinator.py
   - run_review_pipeline(task_id, task_type, payload, executor_output) -> ReviewResult
   - ReviewResult dataclass: {verdicts: list, commitments: list, consensus: str, all_verified: bool}
   - Orchestrates 3 reviewers: GPT-4o #1, GPT-4o #2, Claude (clean context, 3rd reviewer)
   - Step 1: each reviewer computes verdict independently
   - Step 2: each reviewer submits hash commitment (hash only, no verdict revealed)
   - Step 3: all hashes collected
   - Step 4: reveal phase -- verify each commitment
   - Step 5: evaluate consensus (2/3 rule)
   - If any commitment fails verification: raise SecurityViolationError, log event

5. backend/core/review/consensus_eval.py
   - evaluate_consensus(verdicts: list[str]) -> str
   - Returns: "3_OF_3_APPROVE", "2_OF_3_APPROVE", "1_OF_3_APPROVE", "0_OF_3_APPROVE"
   - 2+ APPROVE = PASS; fewer = ESCALATE (Phase 4 just returns result, escalation in Phase 5)

6. backend/workers/execution_worker.py -- UPDATE
   - After Claude execution succeeds, instead of immediately setting COMPLETED:
     a. Set status = REVIEWING
     b. Call run_review_pipeline()
     c. Store review result in task.review_result_json
     d. Set status = COMPLETED
   - On review pipeline failure: route to DLQ with reason

7. backend/app/api/v1/tasks.py -- UPDATE get_task()
   - executor field: deserialise executor_output_json (already done)
   - review field: must return structured review object:
     {
       "consensus": "3_OF_3_APPROVE",
       "reviewers": [
         {"model": "gpt-4o", "verdict": "APPROVE", "confidence": 0.92, "commitment_verified": true},
         {"model": "gpt-4o", "verdict": "APPROVE", "confidence": 0.89, "commitment_verified": true},
         {"model": "claude-sonnet-4-6", "verdict": "APPROVE", "confidence": 0.91, "commitment_verified": true}
       ],
       "completed_at": "<timestamp>"
     }

8. Manual test scripts:
   - docs/testing/manual-test-scripts/MT-005-review-complete.ps1
     - Submit task, poll every 5s until COMPLETED or FAILED (max 120s -- review adds time)
     - Validate: status=COMPLETED, review.consensus present, review.reviewers array of 3
     - Validate: all 3 commitment_verified=true
     - Validate: executor.model AND review present simultaneously

### IMPORTANT: Third reviewer is Claude with clean context

The third reviewer calls Claude (claude-sonnet-4-6) but with:
- A completely different system prompt (reviewer role, not executor role)
- NO knowledge of who executed the task
- NO knowledge of the other two reviewers' verdicts
- A fresh nonce for its own commitment
This provides model diversity in the review pipeline as per D-06.

### GPT-4o reviewer system prompt (use exactly):

  "You are an independent quality reviewer for an AI compliance platform.
   You have no knowledge of who produced the output you are reviewing.
   Assess whether the following AI output is:
   1. Factually accurate relative to the provided input
   2. Complete -- does it address all required elements
   3. Free from hallucination -- does it claim anything not supported by input
   4. Appropriately calibrated -- is the confidence score justified
   5. Safe -- does it flag appropriate caveats

   Respond with ONLY a valid JSON object:
   {
     \"verdict\": \"APPROVE\" | \"REJECT\",
     \"reasoning\": \"<2-4 sentence explanation>\",
     \"confidence\": <float 0.0-1.0>
   }
   Do not include any text outside the JSON object."

### Claude third-reviewer system prompt (use exactly):

  "You are an independent output reviewer for a compliance platform.
   You did not produce the output you are reviewing.
   Your task is to assess whether this AI output is accurate, complete, and well-reasoned.

   Respond with ONLY a valid JSON object:
   {
     \"verdict\": \"APPROVE\" | \"REJECT\",
     \"reasoning\": \"<2-4 sentence explanation>\",
     \"confidence\": <float 0.0-1.0>
   }
   Do not include any text outside the JSON object."

---

## MANUAL TEST MT-005

### MT-005: Review Pipeline Complete
  PRECONDITIONS:
    - Real ANTHROPIC_API_KEY and OPENAI_API_KEY in .env
    - All containers running (api, postgres, redis, celery-worker)
    - MT-004 passing (Phase 3 complete)
  INPUT: POST /api/v1/tasks (same body as MT-004)
  POLL: GET /api/v1/tasks/{task_id} every 5 seconds, max 120 seconds
  EXPECTED FINAL RESPONSE:
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
      "consensus": "3_OF_3_APPROVE" | "2_OF_3_APPROVE",
      "reviewers": [
        {"model": "gpt-4o", "verdict": "APPROVE", "confidence": <float>, "commitment_verified": true},
        {"model": "gpt-4o", "verdict": "APPROVE", "confidence": <float>, "commitment_verified": true},
        {"model": "claude-sonnet-4-6", "verdict": "APPROVE", "confidence": <float>, "commitment_verified": true}
      ],
      "completed_at": "<timestamp>"
    },
    "vertex": null,
    "report_available": false
  }

---

## START INSTRUCTIONS FOR NEW SESSION

1. Read this prompt fully.
2. Read spec: C:\Users\v_sen\Documents\Projects\0001_Hack0014_Vertex_Swarm_Tashi\doc\POC-ENGINE-PRODUCT-SPEC-v1.md
3. Check git: powershell -ExecutionPolicy Bypass -File run.ps1 -cmd "git log --oneline -5"
4. Read existing files before modifying them (especially execution_worker.py -- needs review pipeline inserted)
5. Write all Phase 4 files via filesystem MCP directly.
6. Run MT-005. Read log from runs\ directly.
7. Commit: 'feat: Phase 4 complete -- review pipeline GPT-4o hash commitment MT-005 PASS'

DO NOT proceed to Phase 5 until MT-005 passes.
Phase 5: Vertex consensus integration.
Phase 6: Reporting layer + EU AI Act export.
