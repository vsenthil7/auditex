# Auditex -- Phase 7 Build Prompt
# Dashboard Frontend (React) + Real-Time Task Status Polling
# Paste this entire file into a new Claude session to continue the build.

---

## PRODUCT: Auditex -- AI Workflow Compliance Platform
## SESSION: Phase 7 -- Dashboard Frontend

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
- backend/app/middleware/auth.py    -- X-API-Key Redis-backed validation
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

### Phase 6 -- Reporting Layer (commit bed38f1)
- backend/core/reporting/poc_generator.py
- backend/core/reporting/eu_act_formatter.py
- backend/workers/reporting_worker.py
- backend/db/repositories/report_repo.py
- backend/db/migrations/versions/0002_add_report_available.py
- backend/app/api/v1/reports.py
- backend/app/api/v1/tasks.py     (updated: report_available from real column)
- backend/workers/celery_app.py   (updated: reporting_worker in include=[])
- backend/workers/execution_worker.py (updated: dispatches reporting task)
- backend/app/main.py             (updated: reports router registered)
- MT-007 PASSED: 9/9 checks

Test API key: auditex-test-key-phase2
System agent UUID: ede4995c-4129-4066-8d96-fa8e246a4a10

---

## PHASE 7 GOAL: Dashboard Frontend

By end of Phase 7, MT-008 must pass:
- Navigate to http://localhost:3000
- Dashboard loads without errors
- Submit a task via the UI form
- Task appears in the task list with live status updates
- Status updates in real time: QUEUED → EXECUTING → REVIEWING → FINALISING → COMPLETED
- Once COMPLETED, "View Report" button becomes active
- Clicking "View Report" shows the PoC report with plain_english_summary and EU AI Act sections
- The "Export EU AI Act" button downloads the structured JSON

### Frontend stack (from spec S06)
- React 18 + TypeScript
- Vite 5 (build tool)
- Zustand 4 (state management)
- No external UI component library -- Tailwind CSS only (via CDN in dev, PostCSS in prod)
- API client: hand-written typed fetch wrapper (no codegen in Phase 7)

### Architecture: single-page app, no router needed in Phase 7

One page, three panels:
  1. Submit Task panel (top)
  2. Task List panel (left / middle) -- live polling every 3 seconds
  3. Task Detail / Report panel (right) -- shown when a task is selected

### Real-time polling strategy
- No WebSockets in Phase 7 (Phase 8 if needed)
- Zustand store polls GET /api/v1/tasks every 3 seconds for any task in
  QUEUED | EXECUTING | REVIEWING | FINALISING status
- Once COMPLETED, polling for that task stops
- report_available is polled separately every 3 seconds until true
- All polling stops when component unmounts

### API client (frontend/src/services/api.ts)
Typed wrapper around fetch. All calls include X-API-Key header.
Exposes:
  submitTask(body)         -> POST /api/v1/tasks
  getTask(id)              -> GET /api/v1/tasks/{id}
  listTasks(page, size)    -> GET /api/v1/tasks
  getReport(taskId)        -> GET /api/v1/reports/{task_id}
  exportReport(taskId)     -> GET /api/v1/reports/{task_id}/export?format=eu_ai_act

API_KEY and BASE_URL read from environment variables:
  VITE_API_KEY  (default: "auditex-test-key-phase2")
  VITE_API_URL  (default: "http://localhost:8000")

### Files to create

1. frontend/package.json
   Dependencies (all real, versioned):
     react: ^18.3.1
     react-dom: ^18.3.1
     zustand: ^4.5.2
   DevDependencies:
     typescript: ^5.4.5
     vite: ^5.2.11
     @vitejs/plugin-react: ^4.2.1
     @types/react: ^18.3.1
     @types/react-dom: ^18.3.0
     tailwindcss: ^3.4.3
     autoprefixer: ^10.4.19
     postcss: ^8.4.38

2. frontend/tsconfig.json
   Standard React + Vite tsconfig.

3. frontend/vite.config.ts
   Standard Vite React config.
   Dev server: port 3000, proxy /api -> http://localhost:8000

4. frontend/tailwind.config.js
   Content: ["./index.html", "./src/**/*.{ts,tsx}"]

5. frontend/postcss.config.js
   Standard tailwindcss + autoprefixer.

6. frontend/index.html
   Standard Vite entry point.
   Title: "Auditex -- AI Compliance Dashboard"

7. frontend/src/main.tsx
   Standard React 18 createRoot entry.

8. frontend/src/App.tsx
   Root component. Renders three panels.
   Calls useTaskStore on mount to start polling.

9. frontend/src/services/api.ts
   Typed API client as described above.

10. frontend/src/store/taskStore.ts
    Zustand store. State:
      tasks: Record<string, Task>         -- keyed by task_id
      selectedTaskId: string | null
      loading: boolean
      error: string | null
    Actions:
      submitTask(body)                    -- POST, adds to tasks
      refreshTasks()                      -- GET list, merges into tasks
      selectTask(id)                      -- sets selectedTaskId
      startPolling()                      -- setInterval, 3s, calls refreshTasks
      stopPolling()                       -- clearInterval
    Auto-stop polling for a task once status === "COMPLETED" AND report_available

11. frontend/src/types/index.ts
    TypeScript types matching the API response shapes:
      Task, TaskStatus, ExecutorOutput, ReviewResult, VertexProof
      PoCReport, EuAiActExport

12. frontend/src/components/SubmitTaskForm.tsx
    Form to submit a new task.
    Fields:
      task_type (select: document_review | risk_analysis | contract_check)
      document  (textarea, required)
      review_criteria (checkboxes: completeness, income_verification,
                        employment_verification, risk_assessment)
    On submit: calls store.submitTask(), clears form, selects new task.

13. frontend/src/components/TaskList.tsx
    Scrollable list of tasks, newest first.
    Each row shows: task_id (truncated), task_type, status badge, created_at.
    Status badge colours:
      QUEUED     -- grey
      EXECUTING  -- blue (pulsing)
      REVIEWING  -- purple (pulsing)
      FINALISING -- amber (pulsing)
      COMPLETED  -- green
      FAILED     -- red
      ESCALATED  -- orange
    Clicking a row calls store.selectTask(id).
    Selected row is highlighted.

14. frontend/src/components/TaskDetail.tsx
    Shows full detail for the selected task.
    Sections:
      Status + lifecycle timeline (shows which stages are complete)
      Executor output (model, confidence, recommendation)
      Review panel (3 reviewer cards: model, verdict, commitment_verified)
      Vertex proof (event_hash, round, finalised_at)
      Report section (shown when report_available = true):
        - plain_english_summary (rendered as pre-wrap text)
        - EU AI Act accordion: Article 9, Article 13, Article 17
        - "Export EU AI Act JSON" button (triggers download)

15. frontend/src/components/StatusBadge.tsx
    Reusable status badge component.

16. docker-compose.yml -- UPDATE
    Add frontend service:
      build: ./frontend
      ports: "3000:3000"
      environment:
        VITE_API_KEY: auditex-test-key-phase2
        VITE_API_URL: http://localhost:8000
      depends_on: [api]

17. frontend/Dockerfile
    Multi-stage:
      Stage 1 (builder): node:20-alpine, npm ci, npm run build
      Stage 2 (serve):   node:20-alpine, npm install -g serve,
                         serve -s dist -l 3000

### MT-008 manual test script
docs/testing/manual-test-scripts/MT-008-dashboard.ps1
  - Open http://localhost:3000 in browser (Start-Process)
  - Prompt human: "Does the dashboard load without errors? (y/n)"
  - Prompt human: "Fill in the form and submit a task. Does it appear in the list? (y/n)"
  - Prompt human: "Does the status update live without refreshing? (y/n)"
  - Prompt human: "Once COMPLETED, does View Report show the PoC report? (y/n)"
  - Prompt human: "Does the Export button download a JSON file? (y/n)"
  - Each answer must be 'y' for PASS

---

## MT-008 expected behaviour

1. http://localhost:3000 loads the Auditex dashboard
2. Submit form is visible at the top
3. Submitting a task adds it to the task list immediately at QUEUED
4. Status badge updates automatically every 3 seconds without page refresh
5. When status reaches COMPLETED, a "View Report" button appears on the task row
6. Clicking the task shows TaskDetail with all sections populated
7. The report panel appears once report_available = true
8. "Export EU AI Act JSON" downloads the file as auditex-report-{task_id}.json
9. No console errors visible in browser DevTools

---

## START INSTRUCTIONS FOR NEW SESSION

1. Read this prompt fully.
2. Check git: powershell -ExecutionPolicy Bypass -File run.ps1 -cmd "git log --oneline -5"
3. Check frontend/ directory -- what already exists (likely empty scaffold from Phase 0)
4. Check docker-compose.yml -- read current content before modifying
5. Write all Phase 7 files via filesystem MCP directly.
6. Build and start frontend container:
     powershell -ExecutionPolicy Bypass -File run.ps1 -cmd "docker compose up -d --build frontend"
7. Run MT-008. Human validates in browser.
8. Commit: feat: Phase 7 complete -- dashboard frontend MT-008 PASS

DO NOT proceed to Phase 8 until MT-008 passes.
Phase 8: Unit tests + integration tests (pytest backend, Vitest frontend).
