# PHASE 11 — PLAN (no descope, single session)
# Written: 21/04/2026 21:20 BST
# Git HEAD at plan time: 3a848c7
# Scope: close every gap between POC-ENGINE-PRODUCT-SPEC-v1.md S02–S03 and the current codebase, in one session, while holding pytest + vitest at 100%.

## Mission

Close every architecture gap. 10 components. No descope. Keep pytest 275/275 and vitest 93/93 at 100% while landing the new code. Each new module ships with tests authored in the same commit. Commit-first, push between items.

## The 10 gaps (from spec vs. built comparison at 21:17)

Ranked for demo impact × judge-defensibility, but all 10 ship in Phase 11.

### Tier A — regulatory/compliance value (do first)
1. **`core/reporting/export_signer.py`** + `/api/v1/reports/{id}/sign` — signs EU AI Act JSON exports with org private key; returns signed bundle `{report, signature, public_key, algorithm}`. RSA-PSS-SHA256 via `cryptography`. New org key generated once per container via `/run/secrets/org_private_key.pem` OR env fallback. Response body includes base64-encoded signature + hash of canonical JSON.
2. **`core/consensus/proof_verifier.py`** + `/api/v1/events/{task_id}/verify` — third-party re-verification of Vertex proof: re-hashes the commitment chain (executor output hash + 3 review hashes), compares against stored event_hash, checks Vertex round monotonicity. Returns `{valid: bool, checks: [...], computed_hash: "...", stored_hash: "..."}`.

### Tier B — failure paths + safety net
3. **`workers/dlq_worker.py`** + `/api/v1/tasks/dlq` + `/api/v1/tasks/{id}/resolve` — Dead Letter Queue for tasks that failed 3× retries. New Celery queue `dlq`. Moves task to `dlq_entries` table. DB migration `0003_create_dlq_entries`. Resolve endpoint takes `{decision: "APPROVE"|"REJECT", human_reviewer, notes}` and re-enters the Vertex pipeline with `human_override=true` flag.
4. **`app/api/middleware/rate_limit.py`** — SlowAPI / custom Redis-backed sliding-window rate limit per API key. Default 60 req/min, override via env. Returns 429 with `Retry-After` header.
5. **`app/api/middleware/logging.py`** — structured JSON request/response logs via `structlog`. Includes request_id UUID, path, method, status, latency_ms, api_key_prefix (first 8 chars).

### Tier C — workflow & integration
6. **`services/notification_service.py`** + **`app/api/v1/webhooks.py`** — outbound webhook delivery on task completion. New `webhooks` table (url, secret, events[], active). POST to registered URL with HMAC-SHA256 signature header. Retry 3× on non-2xx. Endpoints: `POST /api/v1/webhooks`, `GET /api/v1/webhooks`, `DELETE /api/v1/webhooks/{id}`, `POST /api/v1/webhooks/{id}/test`.
7. **`services/redis_service.py`** — thin Redis wrapper (get/set/delete/expire/incr/publish). Replace scattered `redis.Redis()` instantiations in foxmq_client, vertex_client, context_manager with the single service.
8. **`core/execution/context_manager.py`** — Redis-backed context store for multi-step workflows. Key pattern `context:{task_id}:{step_name}`, TTL 24h. Used by the coming amendment-resubmit flow and any future multi-step task_type. Does NOT modify existing happy-path; single-step tasks bypass it.
9. **`core/execution/task_runner.py`** — thin orchestrator lifted out of `execution_worker.py`. Moves the execute→review→finalise sequencing into a testable module. Worker becomes a Celery-task shim around `TaskRunner.run()`. Keeps all 275 backend tests green by preserving call-sites.
10. **`core/ingestion/task_router.py` + `schema_validator.py` + `agent_registry.py`** — bundle: JSON-Schema validation of incoming `POST /api/v1/tasks` payloads (`document` required, `review_criteria` enum list, `task_type` enum), proper 422 errors on violation; `task_router` dispatches to the right executor based on task_type (currently only Claude, but the plug-point is what the spec asked for); `agent_registry` exposes CRUD on agents — `POST /api/v1/agents`, `GET /api/v1/agents`, `DELETE /api/v1/agents/{id}` — agents persist in existing `agents` table.

## Test coverage commitment

- **Every new file ships with tests in the same commit.** No "tests later" — that's how we drifted in Phase 10.
- **Pytest stays at 100%** (275 → ~350 tests). New files add new statements; tests must cover them before the run passes threshold.
- **Vitest stays at 100%** — only the frontend surfaces that touch new endpoints (`/verify`, `/sign`, `/dlq`, `/webhooks`) will grow, and each new component gets a matching `.test.tsx` file.
- **Playwright** — add 5 new specs: `signed-export.spec.ts`, `proof-verify.spec.ts`, `dlq-flow.spec.ts`, `webhooks.spec.ts`, `rate-limit.spec.ts`. Existing 26 tests must remain green.

## Ordering — execute top-to-bottom, commit after each

| # | Module | New files | DB migration | Est. tokens |
|---|--------|-----------|--------------|-------------|
| 1 | Reading + refactor plan | — | — | low |
| 2 | `export_signer.py` + signing endpoint + tests | 3 | 0003 add `report_signatures` | medium |
| 3 | `proof_verifier.py` + verify endpoint + tests | 2 | none | medium |
| 4 | `dlq_worker.py` + DLQ table + endpoints + tests | 4 | 0004 add `dlq_entries` | high |
| 5 | `rate_limit.py` middleware + tests | 2 | none | medium |
| 6 | `logging.py` middleware + tests | 2 | none | low |
| 7 | `notification_service.py` + `webhooks.py` route + webhooks table + tests | 4 | 0005 add `webhooks` | high |
| 8 | `redis_service.py` + refactor call-sites + tests | 1 + edits | none | medium |
| 9 | `context_manager.py` + tests | 2 | none | low |
| 10 | `task_runner.py` + extract from execution_worker + tests | 1 + edits | none | medium |
| 11 | Ingestion bundle: `task_router.py`, `schema_validator.py`, `agent_registry.py` + agents endpoints + tests | 4 + edits | none | high |
| 12 | 5 new Playwright specs | 5 | none | medium |
| 13 | Project-Status v3 rollup + final README + DoraHacks submission | 3 | none | medium |

## Non-negotiables carried forward from Phase 10

- **Commit-first**: every file edit → commit → push → test. Never stack 2+ uncommitted edits.
- **Backup before overwrite**: destination exists → `_backup/FILENAME_YYYYMMDD-HHMM.ext` before the new write.
- **100% threshold stays 100%** — if v8/coverage.py flag a gap, either write the test or explicitly justify a pragma with a paragraph of reasoning. No silent threshold drops.
- **No compact without asking.**
- **ops.ps1 is the only operations interface.**
- **Logs in `runs/` — never pasted.**

## Exit criteria (Phase 11 DONE)

- [ ] All 10 gaps closed, files exist at spec paths
- [ ] `ops.ps1 -action pytest` → **100% all metrics**, test count ≥ 350
- [ ] `ops.ps1 -action vitest` → **100% all metrics**, test count ≥ 100
- [ ] `ops.ps1 -action playwright` → **31/31 tests green** (26 existing + 5 new)
- [ ] `docker compose ps` → 6 services, all healthy
- [ ] `Project-Status/Auditex_Status_Rollup_Phase11-open.xlsx` reflects new state
- [ ] README.md written, DoraHacks fields filled, both committed
- [ ] All commits pushed to `origin/main`

## Risk register

- **Risk 1**: Extracting `task_runner.py` from `execution_worker.py` may temporarily break the 275 pytest tests. **Mitigation**: do #10 last; keep the original file paths working by re-exporting symbols; run pytest between each small refactor step.
- **Risk 2**: Alembic migration 0003/0004/0005 on a live postgres container. **Mitigation**: `ops.ps1 -action migrate` (new), run against dev DB first; Docker volumes mean we can drop-and-recreate if needed.
- **Risk 3**: Adding rate-limit middleware may 429 the existing Playwright suite (submits 9 tasks in sequence). **Mitigation**: rate limit header defaults to 120/min, way above test throughput; tests use the same key so bucket is shared.
- **Risk 4**: New webhooks worker hits real external URLs → flaky CI. **Mitigation**: webhook tests use httpserver fixture (local), never real URLs.
- **Risk 5**: Context-window budget in one session. **Mitigation**: this plan is explicit about ordering, so mid-session handoff is possible. If the session runs out before #12+#13, README + submission can land in a micro-session with a clean git state.
