# PHASE 12 — PLAN (no descope, full coverage repayment + architecture docs)

- **Written:** 22/04/2026 05:02 BST
- **Git HEAD at plan time:** `8599b3d` (main, pushed)
- **Pytest at plan time:** 532/532 @ 100% coverage across 6558 statements
- **Vitest at plan time:** 93/93 (pre-Phase-11 baseline — Phase 11 UI owed)
- **Playwright at plan time:** 26/26 (pre-Phase-11 baseline — Phase 11 E2E owed)

## Mission

Repay the Phase 11 scope-shrink in two places:

- **Gap A:** Phase 11 shipped 6 new backend feature-surfaces with zero frontend and zero frontend tests. Build them all now, with vitest + playwright coverage on every one, and hold 100% across the board.
- **Gap B:** `backend/core/ingestion/schema_validator.py` is a home-grown JSONSchema-subset validator. Replace with `jsonschema==4.23.0` (the market-standard library used by OpenAPI / FastAPI ecosystem).

Also land the Phase 12 architecture-documentation + full traceability pack, and prep the submission.

## Standing rules that govern this plan (from CLAUDE_RULES.md + handoff)

- **COMMIT-FIRST HARD RULE.** EDIT → COMMIT → PUSH → TEST. Every commit via `ops.ps1 commit-auto` then `ops.ps1 git-push`, never raw git.
- **100% line + branch coverage** on every new file + every new test scenario. Floor never drops.
- **One commit per logical unit.** Each feature + tests + E2E landing = its own commit.
- **Broken-state commits are DESIRED.** If a step leaves the tree red, commit that red as `[FIX]` follow-up rather than stacking edits.
- **No scope shrink.** If tempted, flag to the user and get explicit sign-off first.
- **FILE BACKUP RULE.** Before editing / deleting any file, `_backup/<name>_YYYYMMDD-HHMM.ext` in-place first. Applies to docs + schema_validator.py + any existing file.
- **Logs live in `runs/`** — never pasted into chat.

---

## The work, in execution order

### Step 1 — Plan (this file)

Produce this file, show it to the user, wait for explicit go-ahead before any code change. No commits yet.

### Step 2 — jsonschema dependency swap (1 commit + 1 [FIX] if needed)

Replace the home-grown validator with `jsonschema==4.23.0` while keeping the public signature `validate_payload(schema, payload) -> (ok: bool, errors: list[str])`.

**Files touched:**

| File | Change |
|---|---|
| `backend/requirements.txt` | add `jsonschema==4.23.0` |
| `backend/core/ingestion/schema_validator.py` | backup, then replace internals with `jsonschema.Draft202012Validator`. Public `validate_payload()` signature stays identical. |
| `backend/tests/unit/test_schema_validator.py` | adjust only error-message string assertions where `jsonschema`'s wording differs from ours; all existing test scenarios stay. |

**Sequence:**

1. `ops.ps1 commit-auto` the plan file first (Step 1 close).
2. `_backup/schema_validator.py_20260422-HHMM.py` alongside source.
3. Edit `requirements.txt` + `schema_validator.py`.
4. `ops.ps1 -action docker-build` (~60–90s) — rebuild `api` + `celery-worker` so the new pip install lands.
5. `ops.ps1 -action docker-up`.
6. Sanity check: `docker compose exec -T api python -c "import jsonschema; print(jsonschema.__version__)"`.
7. `ops.ps1 commit-auto "[REFACTOR] ingestion: replace home-grown validator with jsonschema==4.23.0 (Phase 12 Step 2)"` → push.
8. `ops.ps1 -action pytest` — must stay 532/532 @ 100%. If red, `[FIX]` commit → push → re-run until green.

**Acceptance:** pytest 100%, no statement-count drop in covered modules, import sanity check passes.

### Step 3 — Frontend + vitest + playwright for Phase 11 features (6 commits, 1 per feature)

Each feature = one commit containing: React component(s) + vitest unit tests + playwright spec + any `services/api.ts` / `types/index.ts` / `App.tsx` wiring. 100% coverage on every new file before the commit lands. After each feature commit: run full `pytest` + `vitest` + `playwright`, all three must be green.

Feature breakdown — **all 6 ship, no descope:**

#### 3a — Export signing UI

- **Backend endpoints already live:** `POST /api/v1/reports/{task_id}/sign`, `GET /api/v1/reports/{task_id}/export?signed=true`, `GET /api/v1/events/{task_id}/verify` (proof verify).
- **Frontend components to add:**
  - `frontend/src/components/SignReportButton.tsx` — Sign button on report detail; shows signature hex + public_key_id + algorithm after success; "Download signed bundle" link.
  - `frontend/src/components/VerifySignatureDialog.tsx` — client-side canonical-JSON recomputed-hash viewer; calls `/events/{id}/verify` and renders checks list.
- **Edited:** `TaskDetail.tsx` (mount SignReportButton when report exists), `services/api.ts` (add `signReport`, `exportSignedReport`, `verifyProof`), `types/index.ts` (add `SignedReport`, `VerifyResult`).
- **Vitest to add:**
  - `frontend/src/tests/SignReportButton.test.tsx`
  - `frontend/src/tests/VerifySignatureDialog.test.tsx`
  - extend `frontend/src/tests/api.test.ts` (new methods)
  - extend `frontend/src/tests/types.test.ts` (new types)
- **Playwright to add:** `frontend/tests/signed-export.spec.ts` — happy path: submit task → complete → sign → download signed bundle → verify proof dialog shows all checks green.

#### 3b — DLQ viewer

- **Backend endpoints already live:** `GET /api/v1/dlq/`, `GET /api/v1/dlq/{id}`, `POST /api/v1/dlq/{id}/retry`, `POST /api/v1/dlq/{id}/resolve`.
- **Frontend components to add:**
  - `frontend/src/components/DlqPage.tsx` — list entries with status filter pills (NEW / RETRYING / RESOLVED / REJECTED), per-row Retry + Resolve buttons, JSON-payload peek modal.
  - `frontend/src/components/DlqEntryRow.tsx` — row component for testability in isolation.
  - `frontend/src/store/dlqStore.ts` — zustand store mirroring `taskStore.ts` pattern (list fetch + 5s refresh + action methods).
- **Edited:** `App.tsx` (add `/dlq` route + nav tab), `services/api.ts` (add `listDlq`, `retryDlqEntry`, `resolveDlqEntry`), `types/index.ts` (add `DlqEntry`, `DlqStatus`).
- **Vitest to add:**
  - `frontend/src/tests/DlqPage.test.tsx`
  - `frontend/src/tests/DlqEntryRow.test.tsx`
  - `frontend/src/tests/dlqStore.test.ts`
- **Playwright to add:** `frontend/tests/dlq-flow.spec.ts` — navigate to /dlq → filter by NEW → click Retry on one entry → status flips to RETRYING → Resolve → status flips to RESOLVED.

#### 3c — Rate-limit UX

- **Backend middleware already live:** rate-limit headers `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`; 429 with `Retry-After`.
- **Frontend components to add:**
  - `frontend/src/components/RateLimitToast.tsx` — global 429 catcher with Retry-After countdown timer.
  - `frontend/src/hooks/useRateLimitHeaders.ts` — hook exposing `{limit, remaining, reset}` from the most recent response for the existing header chip.
- **Edited:** `services/api.ts` (wrap all requests; parse headers on every response; throw typed `RateLimitError` on 429), `App.tsx` (mount `RateLimitToast`).
- **Vitest to add:**
  - `frontend/src/tests/RateLimitToast.test.tsx`
  - `frontend/src/tests/useRateLimitHeaders.test.ts`
  - extend `api.test.ts` (429 path + Retry-After parsing + header extraction).
- **Playwright to add:** `frontend/tests/rate-limit.spec.ts` — spam N requests past threshold → toast appears → countdown ticks → after countdown, next request succeeds.

#### 3d — Request-ID surfacing

- **Backend middleware already live:** every response gets `X-Request-ID` header; logged in structured JSON.
- **Frontend components to add:**
  - `frontend/src/components/ErrorDialog.tsx` — replaces ad-hoc error displays; shows message + `request_id` + copy-to-clipboard button.
- **Edited:** `services/api.ts` (capture `X-Request-ID` on every response; attach to thrown errors), existing components switch error-rendering paths to mount `ErrorDialog`.
- **Vitest to add:**
  - `frontend/src/tests/ErrorDialog.test.tsx`
  - extend `api.test.ts` for request-id extraction + propagation paths.
- **Playwright to add:** `frontend/tests/request-id.spec.ts` — induce a deliberate 500 via a known-bad task payload → ErrorDialog appears → request_id visible → clipboard button copies value.

#### 3e — Webhooks admin

- **Backend endpoints already live:** `POST /api/v1/webhooks`, `GET /api/v1/webhooks`, `GET /api/v1/webhooks/{id}`, `DELETE /api/v1/webhooks/{id}`, `POST /api/v1/webhooks/{id}/deliver`, `GET /api/v1/webhooks/{id}/deliveries`.
- **Frontend components to add:**
  - `frontend/src/components/WebhooksPage.tsx` — list + register form + delete confirmation.
  - `frontend/src/components/WebhookRegistrationForm.tsx` — URL + secret + events checklist + test-fire button.
  - `frontend/src/components/WebhookDeliveryHistory.tsx` — per-subscription deliveries table (status code, timestamp, attempt #, last_error).
  - `frontend/src/store/webhooksStore.ts`.
- **Edited:** `App.tsx` (add `/webhooks` route + nav tab), `services/api.ts` (add 6 methods), `types/index.ts` (`WebhookSubscription`, `WebhookDelivery`).
- **Vitest to add:**
  - `frontend/src/tests/WebhooksPage.test.tsx`
  - `frontend/src/tests/WebhookRegistrationForm.test.tsx`
  - `frontend/src/tests/WebhookDeliveryHistory.test.tsx`
  - `frontend/src/tests/webhooksStore.test.ts`
- **Playwright to add:** `frontend/tests/webhooks.spec.ts` — register webhook → appears in list → test-fire → delivery row appears with 200/4xx status → delete → removed from list.

#### 3f — Agent registration with schema-driven validation

- **Backend endpoints already live:** `POST /api/v1/agents`, `GET /api/v1/agents`, `GET /api/v1/agents/{id}` (and payload validation runs through the now-jsonschema-backed `validate_payload`).
- **Frontend components to add:**
  - `frontend/src/components/AgentsPage.tsx` — list + register form.
  - `frontend/src/components/AgentRegistrationForm.tsx` — name + version + JSON-schema textarea; client-side JSON parse check; surfaces 422 field-paths from backend cleanly.
  - `frontend/src/store/agentsStore.ts`.
- **Edited:** `App.tsx` (add `/agents` route + nav tab), `services/api.ts` (add agent methods), `types/index.ts` (`Agent`, `AgentSchemaError`).
- **Vitest to add:**
  - `frontend/src/tests/AgentsPage.test.tsx`
  - `frontend/src/tests/AgentRegistrationForm.test.tsx`
  - `frontend/src/tests/agentsStore.test.ts`
- **Playwright to add:** `frontend/tests/agents.spec.ts` — register agent with valid schema → appears in list → register with invalid JSON → inline error → register with valid JSON but schema violation (e.g. `minLength` on non-string) → backend 422 path field rendered inline.

**Commit cadence for Step 3:** exactly 6 commits, one per feature (3a…3f). After each commit: run all three suites, all must pass before moving on.

### Step 4 — Architecture enhancement + full traceability (multiple commits, one per doc)

1. `docs/architecture/_backup/arch_20260422_<HHMM>/` — snapshot any existing architecture files first.
2. Produce or refresh:
   - `docs/requirements.md` — numbered requirements `REQ-001` … `REQ-NNN` drawn from POC-ENGINE-PRODUCT-SPEC-v1.md + everything shipped through Phase 11 + the Phase 12 UI work.
   - `docs/use-cases.md` — `UC-001` … use-case scenarios mapped to requirements.
   - `docs/user-flows.md` — mermaid flow diagrams (submit task, sign report, review DLQ entry, register webhook, register agent, proof verify).
   - `docs/architecture/HLD.md` — high-level design: containers, services, queues, DB, external calls (Claude / OpenAI / Vertex / webhooks).
   - `docs/architecture/LLD.md` — component-by-component low-level design: for each backend module and each frontend component, show inputs / outputs / dependencies / failure modes.
   - `docs/traceability.md` — full matrix with one row per REQ:
     `REQ <-> UC <-> UserFlow <-> Arch-section <-> HLD-section <-> LLD-section <-> Code file <-> Pytest file <-> Vitest file <-> Playwright spec`
3. Every row in the traceability matrix has a test-coverage cell that is either ✅ (test exists) or 🟡 (flagged follow-up with GW item ID).
4. Commit cadence: one commit per doc (6 commits). After the matrix commit, run all three test suites one more time to confirm nothing drifted.

### Step 5 — Enhancement discussion + submission prep

1. **Ask the user:** "Anything to enhance before submission?" Wait for answer.
2. If enhancements requested: implement with the same 100% coverage rule (commit-first, one commit per enhancement, all three suites green each time).
3. **Submission prep (1–2 commits):**
   - Update `README.md` with Phase 11 + Phase 12 feature summary.
   - Update `docs/PROJECT_STATUS.md` (currently stale — dated 2026-04-06, shows playwright 11/11; needs to reflect the new reality).
   - Create `Project-Status/Auditex_Status_Rollup_Phase12-open.xlsx` by copying the Phase 11 rollup and filling in Phase 12 rows.
   - `docs/README.demo.md` — short demo script (flow through sign → DLQ → webhook fire → agent register → proof verify).
   - Final green check: pytest + vitest + playwright all 100%.
   - `ops.ps1 commit-auto "[RELEASE] v1.0-submission: Phase 11 + Phase 12 complete, all suites green"`.
   - Push, tag as `v1.0-submission`, verify on GitHub. **Note:** `git tag` is not yet in ops.ps1 → will need to extend ops.ps1 with a `git-tag` action first (per "OPS.PS1 GIT COVERAGE RULE" — no raw git for one-shot ops). Flagging this as the one ops.ps1 extension required this session.

---

## Test-coverage accounting

| Suite | At plan time | After Step 2 | After Step 3 (6 commits) | After Step 4 | After Step 5 | Floor |
|---|---:|---:|---:|---:|---:|---:|
| pytest | 532 / 532 | ≥532 / same | ≥532 / same | ≥532 / same | ≥532 / same | 100% |
| vitest | 93 / 93 | 93 / 93 | ~160 / ~160 | same | same | 100% |
| playwright | 26 / 26 | 26 / 26 | 32 / 32 | same | same | 100% |

Vitest estimate assumes ~10–12 new test files across Step 3 at ~5–8 cases each; exact count known as each commit lands.

---

## Dependency changes

| Where | Change | Why |
|---|---|---|
| `backend/requirements.txt` | `jsonschema==4.23.0` added | Market-standard validator; retires home-grown subset (Gap B). |
| `frontend/package.json` | No production deps planned; vitest + playwright already present. If the rate-limit hook needs a timer util I'll flag before pulling one. | Keep deps minimal. |

---

## ops.ps1 extensions required this session

Per "OPS.PS1 GIT COVERAGE RULE", these must be added in a single extension pass before they're used (no raw git, no exceptions):

1. `git-tag <name> [<message>]` — needed at Step 5 for `v1.0-submission`.

That's the only one I foresee. If Step 3 turns up another (e.g. selective `git-add`), I'll extend in a batched second pass rather than add them one at a time.

---

## Risk log

1. **Existing `test_schema_validator.py` may hard-assert our specific error-message strings.** `jsonschema`'s messages differ. Mitigation: adjust only the assertion strings; keep scenarios + count identical.
2. **Vitest coverage on zustand stores** — Phase 10–11 patterns suggest the `create<...>()` factory runs eagerly; ensure new stores are covered at module-load time.
3. **Playwright timing under Docker on Windows** — previous sessions saw flake on slow API starts. Mitigation: rely on existing `webServer` config; don't touch timing defaults; if flake emerges, debounce with `page.waitForResponse` on the specific API call rather than hard sleeps.
4. **docker-build time per feature commit** — Step 3 doesn't need rebuilds (frontend is served by Vite dev in dev; tests run inside `api` which doesn't change). Step 2 is the only rebuild.
5. **PROJECT_STATUS.md is stale.** Refresh slot is Step 5 per handoff; not touching it earlier so the submission commit captures the full final truth.

---

## What I will NOT do unilaterally

- Rename any existing component.
- Delete `frontend/tests/*.log` files (108+ old playwright runs clutter the folder, but deleting is out of scope).
- Touch `docs/testing/runs/*.json` sample reports.
- Add any production frontend dep beyond what's already in `package.json`.
- Compact the chat.

If any of these become necessary mid-session, I'll stop and ask.

---

## Expected end-of-session state

- `main` @ some commit after `8599b3d` with roughly **10–14 new commits** landed and pushed.
- Tag `v1.0-submission` on GitHub.
- pytest 100%, vitest 100%, playwright 100%.
- `docs/requirements.md`, `docs/use-cases.md`, `docs/user-flows.md`, `docs/architecture/HLD.md`, `docs/architecture/LLD.md`, `docs/traceability.md` all present and cross-linked.
- `Project-Status/Auditex_Status_Rollup_Phase12-open.xlsx` reflecting Phase 12 rows.
- `README.md` + `docs/PROJECT_STATUS.md` both fresh.
- `docs/README.demo.md` present.

---

## Go / no-go

Awaiting explicit go-ahead from the user before touching any code. If any step above needs adjustment — scope, ordering, interpretation — now is the moment to flag it.
