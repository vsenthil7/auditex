# PHASE 11 HANDOFF — Session open
# Written: 21/04/2026 21:22 BST
# Git HEAD at handoff: 3a848c7
# Deadline: 22/04/2026 03:00 BST (~5h 38m from write time)

## CURRENT STATE (verified 21:20 BST)

- Git HEAD: `3a848c7` — "[FIX] playwright error-states TC-16a: use .bg-red-50.border-red-200 banner selector"
- Working tree: clean, `origin/main` in sync
- Docker: 6/6 services running (postgres, redis, foxmq, celery-worker, api, frontend)
  - foxmq, postgres, redis healthchecks green
  - api, celery-worker, frontend have no healthcheck but are up
- Backend pytest: **275/275 at 100% lines/branches/statements/functions** (log `ops_pytest_20260421_194822.log`)
- Frontend vitest: **93/93 at 100% all metrics** (log `ops_vitest_20260421_205455.log`)
- Playwright: **25/26 passing → 26/26 after `3a848c7` fix** (needs re-run to confirm; last full log `ops_playwright_20260421_210314.log`)
- FoxMQ: LIVE — real Tashi BFT broker, Vertex rounds incrementing
- DB: 124 COMPLETED, 20 FAILED (historical); 0 active

## WHAT THIS SESSION DOES

**ALL 10 architecture gaps, no descope, one session.** See `docs/PHASE11-PLAN.md` for the full plan. Summary:

1. `core/reporting/export_signer.py` + signed EU AI Act JSON export
2. `core/consensus/proof_verifier.py` + third-party proof verification endpoint
3. `workers/dlq_worker.py` + Dead Letter Queue + resolve endpoint
4. `app/api/middleware/rate_limit.py` — Redis-backed per-key rate limit
5. `app/api/middleware/logging.py` — structured JSON request/response logs
6. `services/notification_service.py` + `app/api/v1/webhooks.py` — outbound webhooks + HMAC
7. `services/redis_service.py` — Redis wrapper, refactor existing call-sites
8. `core/execution/context_manager.py` — Redis-backed multi-step context
9. `core/execution/task_runner.py` — extract orchestration from `execution_worker.py`
10. `core/ingestion/task_router.py` + `schema_validator.py` + `agent_registry.py` + agents CRUD endpoints

Each ships WITH tests in the same commit. Pytest stays 100%, vitest stays 100%, playwright gains 5 new specs.

## SESSION START RITUAL (run these FIRST, in order)

```
1. Read this file (PHASE11-HANDOFF-PROMPT.md) — end of this block
2. Read C:\Users\v_sen\Documents\Projects\claude-memory\global\CLAUDE_RULES.md
3. Read docs/PHASE11-PLAN.md — the full 10-item plan with ordering table
4. Read doc/POC-ENGINE-PRODUCT-SPEC-v1.md sections S02 and S03 (the architecture spec)
5. Verify state:
   .\ops.ps1 -action git-log           # confirm HEAD = 3a848c7 (or newer if session already started)
   .\ops.ps1 -action docker-ps         # confirm 6/6 services running
6. Confirm baselines still green (optional but recommended):
   .\ops.ps1 -action pytest            # expect 275/275 at 100%
   .\ops.ps1 -action vitest            # expect 93/93 at 100%
   .\ops.ps1 -action playwright        # expect 26/26 after the 3a848c7 fix
7. Start Item 1 of the plan (export_signer.py)
```

## THE NON-NEGOTIABLE RULES (carried forward from Phase 10)

- **Commit-first**: edit → commit → push → test. Never stack 2+ uncommitted edits. Flagged 5× in Phase 10 sessions — this is the one habit that keeps drift out.
- **Backup before overwrite**: if the destination already exists, copy it to `_backup/FILENAME_YYYYMMDD-HHMM.ext` BEFORE writing the new version. Example: `_backup/Auditex_Status_Rollup_Phase10-open_20260421-2054.xlsx`.
- **100% means 100%**. If coverage flags a gap, either (a) write the test, or (b) remove the dead code, or (c) add a `/* v8 ignore next */` / `# pragma: no cover` with a paragraph of justification. Never lower the threshold silently.
- **Never compact chat without asking Senthil first.**
- **ops.ps1 is the only operations interface**. No bare `docker compose up`, no bare `git push`. Use the wrapper.
- **Logs live in `runs/`** — never paste them into chat. Link by filename.
- **Senthil types fast and casually** — interpret intent, don't be pedantic.
- **Ops commands need `-ExecutionPolicy Bypass`**: `powershell -ExecutionPolicy Bypass -File "C:\...\ops.ps1" -action <name>`.
- **Shell calls over ~30–45s will time out** — don't embed long `Start-Sleep`. Poll in separate shorter calls.

## KEY FILE PATHS (existing, don't break)

| Area | File | Role |
|---|---|---|
| Root | `ops.ps1` | Ops wrapper — 15 actions including `pytest`, `vitest`, `playwright`, `commit-auto`, `git-push`, `diag` |
| Root | `docker-compose.yml` | 6-service stack; `USE_REAL_VERTEX=true` on api + celery-worker |
| Backend | `backend/app/main.py` | FastAPI app, lifespan |
| Backend | `backend/app/api/v1/{tasks,reports,agents,health}.py` | REST routes (agents currently just a stub) |
| Backend | `backend/app/api/middleware/auth.py` | X-API-Key auth (valid key: `auditex-test-key-phase2`) |
| Backend | `backend/core/consensus/{foxmq,vertex}_client.py` | FoxMQ publish + Vertex proof (LIVE / STUB) |
| Backend | `backend/core/consensus/event_builder.py` | Event payload construction |
| Backend | `backend/core/execution/claude_executor.py` | Claude API call + JSON extraction |
| Backend | `backend/core/review/{coordinator,gpt4o_reviewer,hash_commitment,consensus_eval}.py` | 3-reviewer pipeline |
| Backend | `backend/core/reporting/{poc_generator,eu_act_formatter}.py` | PoC narrative + EU AI Act JSON |
| Backend | `backend/db/models/{task,agent,event,report,audit_event,base}.py` | SQLAlchemy ORM |
| Backend | `backend/db/repositories/{task,agent,event,report}_repo.py` | Data access layer |
| Backend | `backend/db/migrations/versions/` | Alembic — 0001, 0002 exist; Phase 11 adds 0003, 0004, 0005 |
| Backend | `backend/workers/{celery_app,execution_worker,reporting_worker}.py` | Celery tasks; review/consensus logic inlined in execution_worker (to be extracted in Item 9) |
| Backend | `backend/services/{claude,openai}_service.py` | LLM SDK wrappers |
| Backend | `backend/tests/` | 34 pytest files + conftest + pytest.ini (275 tests, 100%) |
| Frontend | `frontend/src/{App,main}.tsx` | Zustand-wired app shell |
| Frontend | `frontend/src/components/{StatusBadge,SubmitTaskForm,TaskList,TaskDetail}.tsx` | UI (TaskDetail has dead-code cleanup from Phase 10) |
| Frontend | `frontend/src/services/api.ts` | Typed API client |
| Frontend | `frontend/src/store/taskStore.ts` | Zustand store, 3s polling |
| Frontend | `frontend/src/tests/` | 8 vitest files (93 tests, 100%) |
| Frontend | `frontend/vite.config.ts` | Vitest config, 100% threshold all metrics |
| Frontend | `frontend/tests/` | 10 Playwright specs (26 tests) |
| Docs | `doc/POC-ENGINE-PRODUCT-SPEC-v1.md` | Canonical product spec — S02/S03 are the architecture source of truth |
| Docs | `doc/Hack0014-Vertex-Swarm-Challenge-Master-Brief.md` | Hackathon brief |
| Status | `Project-Status/Auditex_Status_Rollup_Phase10-open_v2.xlsx` | Latest rollup (Phase 10 complete) |

## DECISIONS FROM PHASE 10 THAT STAND

- **Dead code was removed, not pragma-ed**, when structurally unreachable:
  - `TaskDetail.tsx` — `isFailed && active` branches deleted (FAILED/ESCALATED status never matches a STAGES entry) — commit `3d75b18`
  - `TaskDetail.tsx` — `badgeColour ?? 'bg-gray-100 text-gray-600'` fallback deleted (every Section call-site already passes a colour when badge is set) — commit `8fe7613`
- **One `/* v8 ignore next */` pragma** stands with justification: `handleExport` in `TaskDetail.tsx` has `if (!task) return` that's only reachable if the export button renders outside the `{report && <button>}` tree, which it never does. Commit `a479913`. Do NOT remove without auditing the render tree.
- **One `# pragma: no cover`** stands on `vertex_client.py` `foxmq_ts` line: mock-closure limitation tested to be impractical. Commit `cf63402`.
- **Vitest config `css: false`** — never load real CSS in tests, jsdom can't parse tailwind at test time.
- **URL.createObjectURL / revokeObjectURL polyfills** in `frontend/src/tests/setup.ts` — jsdom 24 doesn't ship them.

## COMMIT-MESSAGE FORMAT (keep consistent)

- `[TEST] <area>: <what>` — new tests
- `[FIX] <area>: <what>` — bug fix
- `[FEAT] <area>: <what>` — new feature
- `[DOCS] <area>: <what>` — documentation
- `[OPS] <area>: <what>` — tooling / ops.ps1 / Docker / CI

Phase 10 used all of these — scan recent `git log --oneline` for examples.

## WHERE TO WRITE THE NEW CODE (spec paths)

All paths below are from repo root. Create each file the first time it's needed.

```
backend/core/reporting/export_signer.py              # Item 1
backend/app/api/v1/reports.py                        # Item 1 edit — add POST /reports/{id}/sign
backend/tests/test_export_signer.py                  # Item 1 test
backend/db/migrations/versions/0003_report_signatures.py   # Item 1 migration

backend/core/consensus/proof_verifier.py             # Item 2
backend/app/api/v1/events.py                         # Item 2 new route file: GET /events/{task_id}/verify
backend/tests/test_proof_verifier.py                 # Item 2 test
backend/tests/test_api_events.py                     # Item 2 route test

backend/workers/dlq_worker.py                        # Item 3
backend/app/api/v1/dlq.py                            # Item 3 route
backend/db/models/dlq_entry.py                       # Item 3 ORM
backend/db/repositories/dlq_repo.py                  # Item 3 repo
backend/db/migrations/versions/0004_dlq_entries.py   # Item 3 migration
backend/tests/test_dlq_worker.py                     # Item 3 test

backend/app/api/middleware/rate_limit.py             # Item 4
backend/tests/test_rate_limit_middleware.py          # Item 4 test

backend/app/api/middleware/logging.py                # Item 5
backend/tests/test_logging_middleware.py             # Item 5 test

backend/services/notification_service.py             # Item 6
backend/app/api/v1/webhooks.py                       # Item 6 route
backend/db/models/webhook.py                         # Item 6 ORM
backend/db/repositories/webhook_repo.py              # Item 6 repo
backend/db/migrations/versions/0005_webhooks.py      # Item 6 migration
backend/tests/test_notification_service.py           # Item 6 test
backend/tests/test_api_webhooks.py                   # Item 6 route test

backend/services/redis_service.py                    # Item 7
backend/tests/test_redis_service.py                  # Item 7 test
# Item 7 edits: foxmq_client.py, vertex_client.py to route through redis_service

backend/core/execution/context_manager.py            # Item 8
backend/tests/test_context_manager.py                # Item 8 test

backend/core/execution/task_runner.py                # Item 9 — extracted from execution_worker
backend/tests/test_task_runner.py                    # Item 9 test
# Item 9 edits: workers/execution_worker.py becomes a shim

backend/core/ingestion/task_router.py                # Item 10a
backend/core/ingestion/schema_validator.py           # Item 10b
backend/core/ingestion/agent_registry.py             # Item 10c
backend/app/api/v1/agents.py                         # Item 10 edit — full CRUD
backend/tests/test_task_router.py                    # Item 10a test
backend/tests/test_schema_validator.py               # Item 10b test
backend/tests/test_agent_registry.py                 # Item 10c test
backend/tests/test_api_agents.py                     # Item 10 route test

frontend/tests/signed-export.spec.ts                 # Item 12 playwright
frontend/tests/proof-verify.spec.ts                  # Item 12
frontend/tests/dlq-flow.spec.ts                      # Item 12
frontend/tests/webhooks.spec.ts                      # Item 12
frontend/tests/rate-limit.spec.ts                    # Item 12

Project-Status/Auditex_Status_Rollup_Phase11-open.xlsx   # Item 13 (backup v2 before writing)
README.md                                            # Item 13
```

## QUICK SANITY CHECKS IF SOMETHING GOES WRONG

- Test suite broken? — `git stash && .\ops.ps1 -action pytest` to prove baseline. If baseline fails, something in the env shifted, not in your diff.
- Docker service crashed? — `.\ops.ps1 -action diag` prints full state. Usually `docker compose restart <svc>`.
- Playwright flaky? — confirm port 3000 responds: `curl http://localhost:3000` from host. Frontend container may need `docker compose restart frontend`.
- FoxMQ not LIVE? — `.\ops.ps1 -action foxmq-logs` — look for "MQTT broker listening on port 1883".
- Alembic migration conflict? — tests use fresh DB via conftest; production DB may need `docker compose exec api alembic upgrade head`.

## WHAT TO SAY IF ASKED ABOUT PROGRESS MID-SESSION

Keep the rolling counter visible:
- "Item N of 10 done. Pytest X/Y at 100%. Vitest A/B at 100%. Playwright stays at 26/26."
- Never say "close enough" — if a metric isn't 100%, name the exact gap.

## END OF HANDOFF

Resume sequence: read `CLAUDE_RULES.md` → read `PHASE11-PLAN.md` → run `.\ops.ps1 -action git-log` to confirm state → start Item 1.

Good luck.
