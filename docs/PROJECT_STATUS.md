# AUDITEX PROJECT STATUS
# Updated: 2026-04-27 00:13 BST
# Rules: update at end of every work block. Never compact chat without asking. Warn at 50% context.

## PROJECT
- Root: C:\Users\v_sen\Documents\Projects\0001_Hack0014_Vertex_Swarm_Tashi\auditex
- Stack: FastAPI + Celery + PostgreSQL + Redis + React/TS + Playwright in Docker
- Ops: ops.ps1 (actions: git, playwright, status, clear, celery-logs, diag, docker-ps)
- Logs: runs/ops_<action>_<timestamp>.log (read directly, never paste)
- DoraHacks BUIDL #43345 (Track 3 Agent Economy / Vertex Swarm Challenge)

## CURRENT STATUS: HEAD 19ae177 | 565 backend tests pass | 3+ Playwright E2E pass | Article 14 SHIPPED | Demo video refreshed and submitted

## RECENT PHASE: PHASE-14 (Demo Video Refresh) - 2026-04-26 / 2026-04-27

Shipped 11 commits across Page-002 (`52055ed..19ae177`):
- ec34147  V-1 git-first checkpoint - structural-review spec staged
- d2b7781  V-2 extend demo spec with HIL block H-1..H-12 (Article 14 walkthrough)
- 3445000  V-3 demovideo/creation/run-hil-video.ps1 separate runner (already from prior session)
- c808496  V-4 fix - in-spec policy disable+re-enable, real API key, attempt-1 root cause
- 15624f9  V-4 fix2 - H-6 wait regex matches StatusBadge display NEEDS HUMAN (not enum)
- bff71e3  V-4 fix3 - RATE_LIMIT_PER_MINUTE=0 in docker-compose.yml api environment
- 4cdc816  V-5 fix - structural-review.spec.ts beforeAll disables HIL policies
- 2fa6b57  V-2.5 spec rewrite - 6-scenario matrix (3 task types x 2 paths each)
- d090940  V-2.5 runner fix - pre-flight no longer requires required=true on all 3 policies
- ae37913  V-2.6 spec - shutter startup, Oversight Config visit, Articles expansion attempt
- 19ae177  V-2.7 spec - title card on about:blank, arrow-detect Step expansion, Articles sequential

## VIDEO SHIPPED

- Final webm: demo/end-to-end-v4-20260426_234530.webm (15.69 MB)
- Backup: demo/_backup/end-to-end-v4-20260426_234530.webm
- YouTube (Unlisted): https://youtu.be/ydcLTZsgxuk
- DoraHacks BUIDL: https://dorahacks.io/buidl/43345 - updated 27/04/2026 with YouTube URL
- Reply to organisers (Vertex Swarm Challenge): sent 27/04/2026 00:07 BST via DoraHacks message thread

## DEMO CONTENT (v4 video, 6-scenario matrix)

TC-1 contract_check + Auto APPROVE     (HIL disabled, BFT consensus to COMPLETED)
TC-2 contract_check + Human APPROVE     (HIL enabled, reviewer Aoife O'Connor APPROVE)
TC-3 risk_analysis  + Auto REJECT       (HIL disabled, anomaly detected)
TC-4 risk_analysis  + Human OVERRIDES   (HIL enabled, AI APPROVE -> human REJECT)
TC-5 document_review + Auto REQUEST_AMENDMENTS (HIL disabled, missing field flagged)
TC-6 document_review + Human REQUEST_AMENDMENTS (HIL enabled, manual amendments)

Each scenario: caption -> Oversight Config tab visit (policy state visible) -> form fill ->
submit -> wait COMPLETED (or NEEDS HUMAN -> Human Review -> decide -> COMPLETED) ->
detail panel with all 5 Steps expanded -> Articles 9/13/17 opened sequentially ->
Vertex sign + verify -> next scenario.

## RECORDING ATTEMPT HISTORY

7 recording attempts during 26 April:
- 22:10 v4-221000.webm 9.23 MB - V-2 spec (3 outcome paths + HIL block)
- 22:54 v4-225412.webm 15.73 MB - V-2.5 6-scenario, blank screens between, Step 5 not expanded
- 23:20 v4-232006.webm 16.32 MB - V-2.6 with Oversight Config visit, Articles still collapsed
- 23:45 v4-234530.webm 15.69 MB - V-2.7 (FINAL CHOSEN) - fixes all known issues
- 21:02 attempt failed at H-6 (regex /AWAITING.*HUMAN/ vs displayed NEEDS HUMAN)
- 21:25 attempt failed at H-6 (rate limiter 429 on policy re-enable PUT)
- 21:49 attempt failed with 401 (Redis FLUSHDB wiped seeded API key)

## VERIFICATION

- Backend pytest: 565 pass
- Playwright E2E: 14 pass (11 original + 3 HIL E2E from PHASE-13)
- verify-a structural review: 3/3 pass (24 structural assertions across 3 scenes)
- verify-b OCR: skipped (ffmpeg + tesseract not installed locally; not a submission blocker)

## INFRASTRUCTURE CHANGES THIS PHASE

- docker-compose.yml: api environment got RATE_LIMIT_PER_MINUTE: "0" for demo recording.
  Production deployments must set this back. Acknowledged tech debt for PHASE-15.
- .env: RATE_LIMIT_PER_MINUTE=600 added (not actually used because compose has explicit env block; harmless).
- run-hil-video.ps1 pre-flight: no longer requires required=true on all 3 policies.
- structural-review.spec.ts: beforeAll disables HIL policies via API to keep verify-a green.
- end-to-end-demo.spec.ts: full rewrite to 6-scenario matrix with about:blank pre-paint pattern.

## DEFAULT POLICIES (seeded by alembic 0005, current DB state may vary)
- contract_check    required=true, n_of_m=1/1, timeout=null,    auto_commit=false
- risk_analysis     required=true, n_of_m=2/3, timeout=null,    auto_commit=false
- document_review   required=true, n_of_m=1/1, timeout=1440min, auto_commit=true

Note: spec's setPolicy() now toggles required state per scenario at runtime.

## DB STATE
10 tables: agents, alembic_version, audit_events, dlq_entries, human_decisions, human_oversight_policies, reports, tasks, webhook_deliveries, webhook_subscriptions

## API SURFACE
22 endpoints across health, tasks, agents, reports, dlq, events, webhooks, human-review, human-oversight-policies. All require X-API-Key: auditex-test-key-phase2. Default agent_id: ede4995c-4129-4066-8d96-fa8e246a4a10.

## SUBMISSION DOCS GENERATED
- docs/AUDITEX-DORAHACKS-SUBMISSION_20260426-2358.md  - paste-ready for DoraHacks BUIDL description (85% built, 15% funded external work, funding plan 4 tranches, SWOT)
- docs/PHASE-14-PAGE-002-STATUS_20260426-2348.md      - full session handover document
- docs/assets/dorahacks-correspondence/README.md      - placeholder for screenshot of DoraHacks message thread (drag-drop screenshot manually)

## NEXT PHASE: PHASE-15 - POST-SUBMISSION MONITORING + EP-1 KICKOFF

Build prompt at: docs/PHASE-15-BUILD-PROMPT.md

Key items deferred from PHASE-14 (cleanup carry-forward):
- Delete misplaced pages/Page-002-Video-Refresh/, pages/PageN-EP1-Multi-Tenancy/, pages/Page-002-EP1-Multi-Tenancy/
- Move EP-1 multi-tenancy spec to docs/PHASE-N-EP1-MULTI-TENANCY-PROMPT.md
- Write process-violation lesson at claude-memory/global/lessons/session-management/AUDITEX-PHASE-13_session-bootstrap-rules-not-read_20260425.md
- Re-enable RATE_LIMIT_PER_MINUTE > 0 in docker-compose.yml when not recording

Post-submission work (waiting on DoraHacks judging response):
- Monitor DoraHacks for judges' decision
- If shortlisted: prepare for any follow-up demo
- If not shortlisted: pivot to design-partner conversations using AUDITEX-DORAHACKS-SUBMISSION as the deck
- EP-1 multi-tenancy on enhancement/post-submission branch (BLOCKER gap; first commercial pilot prerequisite)


## RECENT PHASE: PHASE-13 (Article 14 Human-in-the-Loop) - 2026-04-25

Shipped 18 commits across Page-001 covering HIL-1 through HIL-16:
- HIL-1..5  9fb612f  Backend foundation: TaskStatus AWAITING_HUMAN_REVIEW; Pydantic schemas; ORM models human_decisions + human_oversight_policies; alembic 0005 migration with seeded defaults; oversight_policy.py with Policy/Decision/QuorumResult dataclasses + N-of-M evaluator + REJECT-overrides + REQUEST_AMENDMENTS-overrides-APPROVE rule; 16 unit tests at 100% line coverage
- HIL-6     6cee29b  Worker gate in execution_worker.py - reads policy after LLM consensus, sets AWAITING_HUMAN_REVIEW, defers Vertex submit
- HIL-7     95d48f1  4 API endpoints (queue, decision, list-policies, upsert-policy) with 404+409+400 validation; migration fix dropping spurious updated_at columns
- HIL-8     50879ca  Celery finalise_after_human_review task; event_builder schema 1.1 with human_decisions_hash; idempotent finalisation
- HIL-9     2d8626a  TaskStatus type + amber pulsing StatusBadge
- HIL-10    30c2e1e  Real HumanReviewPage split-pane UI with decision form (APPROVE/REJECT/REQUEST_AMENDMENTS)
- HIL-11    6a9c10e  Real OversightConfigPage editable table with dirty-row highlight + validation + reload
- HIL-12/13 2d8626a  3-tab nav + api.ts wiring
- HIL-14    f757b69  11 backend integration tests + endpoint return-schema fix
- HIL-15    6a9c10e  3 Playwright E2E (tab nav, config round-trip, full Article 14 flow)
- HIL-16    8f1d424  ENTERPRISE-GAP-REGISTER updated: Gap 3 BLOCKER -> RESOLVED
- DOCS      f1dfc17  Rename pages/Page-002/CSR.md to session_prompt.md (then realised wrong location entirely; Page-002 in pages/ folder is non-standard for auditex - real handoff convention is docs/PHASE-N-*. To clean up in PHASE-14)

## E2E VERIFIED

Live contract_check task flowed: Submit -> Execute -> Review (3 LLMs consensus) -> AWAITING_HUMAN_REVIEW (worker gate fired) -> APPROVE recorded by hil8tester@local -> quorum 1/1 reached -> auto-finalise via Celery -> COMPLETED with Vertex hash 4723d400... -> task_completed audit event includes human_decisions_count=1 with human_decisions_hash for tamper-evidence

## TEST COUNTS
- Backend pytest: 565 passed (added 27 new in PHASE-13: 16 policy unit + 11 API integration)
- Playwright E2E: 14 passed (11 original TC-01..11 + 3 new HIL E2E)
- Pre-PHASE-13 baseline was 538 backend tests

## DEFAULT POLICIES (seeded by alembic 0005)
- contract_check    required=true, n_of_m=1/1, timeout=null,    auto_commit=false
- risk_analysis     required=true, n_of_m=2/3, timeout=null,    auto_commit=false
- document_review   required=true, n_of_m=1/1, timeout=1440min, auto_commit=true

## DB STATE
10 tables: agents, alembic_version, audit_events, dlq_entries, human_decisions, human_oversight_policies, reports, tasks, webhook_deliveries, webhook_subscriptions

## API SURFACE
22 endpoints across health, tasks, agents, reports, dlq, events, webhooks, human-review, human-oversight-policies. All require X-API-Key: auditex-test-key-phase2. Default agent_id: ede4995c-4129-4066-8d96-fa8e246a4a10.

## NEXT PHASE: PHASE-14 - DEMO VIDEO REFRESH FOR DORAHACKS

**Trigger:** DoraHacks email 2026-04-24 10:28 - judges asked for demo video link on BUIDL #43345. Extension granted to Sunday 26 April 2026 EOD.

**Goal:** Refresh end-to-end-demo to include the 12 HIL beats (Article 14 work shipped after original submission video). New video archived in demo/ AND demo/_backup/. Link added to DoraHacks BUIDL.

**Approach:** Path A - extend existing frontend/tests/demo/end-to-end-demo.spec.ts with HIL beats inline. One continuous webm. No DemoForge required - the auditex demovideo/ pipeline (run.ps1 + 3 options) is sufficient.

**Build prompt at:** docs/PHASE-14-BUILD-PROMPT.md

## CARRY-FORWARD CLEANUP (PHASE-14 first action)
- Delete pages/ folder created in error during Page-001 (non-standard location for auditex; real convention is docs/PHASE-N-*)
- Files to remove: pages/Page-002-Video-Refresh/session_prompt.md, pages/PageN-EP1-Multi-Tenancy/session_prompt.md, scripts/write_csr_page002.py (also broken)
- Content from pages/PageN-EP1-Multi-Tenancy/session_prompt.md (EP-1 multi-tenancy spec) should be relocated to docs/PHASE-N-EP1-MULTI-TENANCY-PROMPT.md (deferred until DoraHacks winners announced)

## BRANCH STRATEGY (locked at end of Page-001)
- main = submitted/judged build. Frozen except critical safe fixes (cherry-pick only). Currently HEAD f1dfc17.
- enhancement/post-submission = future EP-1..12 enterprise work (multi-tenancy, asymmetric crypto, SSO, etc). Branched off main when work begins. Merged back after DoraHacks winners announced.

## ENTERPRISE GAP STATUS (from docs/ENTERPRISE-GAP-REGISTER.md, updated in HIL-16)
- 5 BLOCKERS remain (was 6, Gap 3 RESOLVED in PHASE-13)
- Gap 1 (asymmetric crypto, Ed25519 + HSM-integration option) = next critical-path item
- Full 16-gap register in docs/ENTERPRISE-GAP-REGISTER.md
- Full 12-phase enterprise roadmap (EP-1..12, ~5-7M GBP year-1, 18-25 months) discussed in Page-001 chat history; needs to be written as docs/ENTERPRISE-ROADMAP.md in a future page

## CUSTOMER ANALYSIS (from Page-001 brutal roleplay)
Five buyer types analysed:
- Aoife (Irish insurer, EUR 8-25K/yr) - buyable at end of EP-10 self-serve SaaS (~month 5-6)
- Marcus (US SaaS, USD 50-80K/yr) - buyable at EP-11 + SOC 2 Type I (~month 7)
- Klaus (German bank, EUR 280-450K/yr) - buyable at all phases done + Big-4 endorsement letter (~month 18-22)
- Sophie (Big-4 Audit) - wants whitelabel partnership (EUR 150-250K/yr) or acquihire (EUR 2-4M)
- Elena (German hospital DPO) - 24-36 months out; needs ISO 13485 + BSI C5 + PACS integration; AVOID until ARR > 5M GBP

