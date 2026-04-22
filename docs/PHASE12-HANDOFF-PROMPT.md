# Phase 12 Handoff Prompt

**Previous session end: 22/04/2026 04:47 BST**
**Next session: complete the start ritual before touching code.**

## 0. START RITUAL (DO NOT SKIP, DO NOT REORDER)

1. Read this handoff file in full.
2. Read CLAUDE_RULES.md at repo root.
3. Read docs/PROJECT_STATUS.md.
4. Confirm Docker Desktop is running (green whale icon in taskbar).
5. Run git status -- expect working tree clean at HEAD 49bb659.
6. Run ops.ps1 -action pytest and confirm 532/532 @ 100% green before any new work.
7. Report session start timestamp to the user.

## 1. HONEST STATE CHECK -- WHAT IS NOT YET DONE

Phase 11 landed 10 backend items at 100% pytest coverage, but the scope-shrink rule was violated in two places that must be repaid this session:

### Gap A: no frontend / vitest / playwright coverage for Phase 11 features

Phase 11 added these backend surfaces with zero UI and zero frontend tests:

- POST /reports/{task_id}/sign, GET /export?signed=true  (export signing)
- GET/POST /dlq/*, /dlq/{id}/retry, /dlq/{id}/resolve  (dead-letter queue)
- Rate-limit headers (X-RateLimit-Limit, X-RateLimit-Remaining, 429 handling)
- X-Request-ID correlation
- POST/GET/DELETE /webhooks, POST /webhooks/{id}/deliver, GET /webhooks/{id}/deliveries
- Agent CRUD + ingestion (task_router, schema validation errors surfaced in UI)

Current counters still show vitest 93/93, playwright 26/26 -- those are the pre-Phase-11 numbers.

### Gap B: home-grown schema validator instead of jsonschema

backend/core/ingestion/schema_validator.py is a custom implementation. Market standard is jsonschema (used by OpenAPI, FastAPI, etc). Replace it.

## 2. WORK ORDER FOR THIS SESSION

Do these in order. Do not jump ahead. No scope shrink. 100% coverage on every new file and every new test scenario.

### Step 1 -- Write the plan, show it, wait for go-ahead

Before writing any code, produce docs/PHASE12-PLAN.md with:

- List of every frontend component to add/edit
- List of every vitest file to add
- List of every playwright spec to add
- Dep changes (jsonschema add)
- Architecture enhancement plan (see Step 4)

Show the plan to the user. Wait for explicit go-ahead before touching code.

### Step 2 -- Install jsonschema, replace home-grown validator

1. Add jsonschema==4.23.0 to backend/requirements.txt.
2. .\ops.ps1 -action docker-build  (rebuild api + worker images, ~60-90s).
3. .\ops.ps1 -action docker-up.
4. Verify: docker compose exec -T api python -c "import jsonschema; print(jsonschema.__version__)
5. Replace internals of backend/core/ingestion/schema_validator.py with jsonschema.Draft202012Validator while keeping the public validate_payload(schema, payload) -> (ok, errors) signature. Existing test_schema_validator.py tests should all pass -- adjust only error-message assertions.
6. Commit: [REFACTOR] ingestion: replace home-grown validator with jsonschema (Phase 12 Step 2).
7. Pytest -- must stay 100% green.

### Step 3 -- Frontend UI + vitest + playwright for Phase 11 features

Each feature needs: React component(s), vitest unit tests, playwright E2E spec, with 100% coverage, wired into existing tab/nav structure.

Features to build UI for (one commit per feature):

- Export signing: Sign button on Report detail page, display signature hex + key id, verify-signature utility.
- DLQ viewer: new /dlq page -- list entries, filter by status, retry/resolve buttons per row.
- Rate-limit UX: global 429 handler that shows toast + Retry-After countdown.
- Request ID: display in error dialogs for support triage.
- Webhooks admin: new /webhooks page -- register/list/delete subscriptions, test-fire deliver, delivery history.
- Agent registration: agent CRUD form with JSON-schema-driven payload validation.

For each: new vitest file(s), new playwright spec. After each feature commit, run full pytest + vitest + playwright and confirm 100%.

### Step 4 -- Architecture enhancement + full traceability

1. Backup first: copy current docs/architecture/ contents into docs/architecture/_backup/arch_20260422_<timestamp>/.
2. Produce/refresh these documents:
   - docs/requirements.md -- numbered requirements (REQ-001, REQ-002, ...)
   - docs/use-cases.md -- use-case scenarios (UC-001, ...)
   - docs/user-flows.md -- user flow diagrams (mermaid)
   - docs/architecture/HLD.md -- high-level design
   - docs/architecture/LLD.md -- low-level design per component
   - docs/traceability.md -- matrix: REQ <-> UC <-> UserFlow <-> Arch <-> HLD <-> LLD <-> Code file <-> Test file (pytest/vitest/playwright)
3. Every row in the traceability matrix must have a test coverage cell that is either green (has a test) or flagged for follow-up.

### Step 5 -- Enhancement discussion, then submission prep

1. Ask the user: Anything you want to enhance before submission? Wait for answer.
2. If enhancements requested, implement them with the same 100% coverage rule.
3. Submission preparation:
   - Update README.md with Phase 11 + 12 features.
   - Update docs/PROJECT_STATUS.md.
   - Fill in the Phase 12 status rollup spreadsheet (Project-Status/Auditex_Status_Rollup_Phase12-open.xlsx -- create by copying Phase 11 one).
   - Produce a short demo video script or README.demo.md.
   - Final green check: pytest + vitest + playwright all 100%.
   - Push, tag as v1.0-submission, verify on GitHub.

## 3. STANDING RULES -- DO NOT BREAK

- No scope shrink. If tempted, flag it to the user and get explicit sign-off first.
- 100% line + branch coverage on every code file and every test scenario.
- Git-first: ops.ps1 git commit before any build/test operation, no exceptions.
- Commit after each step closes. Never stack uncommitted edits across features.
- Logs stay in runs/ -- never paste into chat.
- User types fast and casually -- interpret intent, do not be pedantic.
- Show start timestamp at session start and end timestamp at session end.
- Never compact chat without asking the user first.
- Market-standard tools always win over home-grown ones. If no standard lib is installed, ASK before rolling your own.

## 4. RUNTIME ENVIRONMENT

- Root: C:\\Users\\v_sen\\Documents\\Projects\\0001_Hack0014_Vertex_Swarm_Tashi\\auditex
- Ops wrapper: ops.ps1
- Shell: powershell -ExecutionPolicy Bypass -Command
- Alembic current: 0004 (head)  (dlq_entries + webhook_subscriptions + webhook_deliveries created)
- Git HEAD: 49bb659  (Phase 11 Item 10 COMPLETE, Phase 11 DONE)

## 5. FINAL GREEN STATE AT PHASE 11 END

- Pytest: 532/532 @ 100% coverage across 6558 statements
- Vitest: 93/93 (pre-Phase-11 baseline -- Phase 11 UI not yet written)
- Playwright: 26/26 (pre-Phase-11 baseline)
- HEAD: 49bb659, pushed

## 6. WHY WE MOVED FAST IN PHASE 11

To answer user directly: we moved fast because we stayed backend-only. The frontend + vitest + playwright tax was deferred -- which is exactly the scope shrink this session must repay. Do not take Phase 11 speed as the norm. Phase 12 is intentionally slower because coverage is holistic: backend + frontend + E2E + docs.
