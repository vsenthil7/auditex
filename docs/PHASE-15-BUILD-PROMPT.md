# PHASE-15 Build Prompt — Enterprise Doc Spine

**Phase:** PHASE-15 - Architecture documents + full requirements traceability to tests
**Trigger:** PHASE-14 video shipped to DoraHacks 27/04/2026. Project pivots from hackathon-grade engineering to enterprise-grade doc spine.
**HEAD at start:** 64e6ddb (Phase-14 close)
**Branch:** main (Phase-15 doc work is reversible reference material; no risk to demo state)
**Next session:** Read this file first.

---

## Why this phase exists (rationale)

Auditex shipped a working POC + Article 14 + 6-scenario demo on DoraHacks BUIDL #43345.
But there is no enterprise doc spine. A regulated buyer (banking, defence, healthcare)
asking "show me your SAD" or "where's your SRS" or "show the requirements traceability
matrix" cannot be answered today. That is a procurement-stopper.

Before any further engineering (Ed25519, multi-tenancy, observability), we lay down the
full doc spine to market standard so that:

- Every existing feature maps to a numbered requirement
- Every numbered requirement maps to a design element + code module + test case
- Every architecture decision made so far is captured in an ADR
- EU AI Act Articles 9/13/14/17 each have a dedicated mapping document, risk plan,
  and quality plan
- GDPR Article 35 DPIA exists for the data flows we already operate

This is reference work that sits BEHIND the product. Engineering resumes at PHASE-16
with this spine in place, so future code changes have a doc home to update.

---

## Scope - 12 documents + 3 existing-MD rewrites

### The 12 new documents (in dependency order)

| # | Doc | Standard | Lives at |
|---|-----|----------|----------|
| 1 | Vision / PRD | IEEE 830 / ISO 25010 | docs/standards/01-VISION-PRD.md |
| 2 | SRS | IEEE 830 / ISO 29148 | docs/standards/02-SRS.md |
| 3 | SAD | ISO 42010 / arc42 / C4 | docs/standards/03-SAD.md |
| 4 | SDD | IEEE 1016 | docs/standards/04-SDD.md |
| 5 | RTM | DO-178C inspired | docs/standards/05-RTM.md |
| 6 | Test Plan | IEEE 829 | docs/standards/06-TEST-PLAN.md |
| 7 | Test Cases | IEEE 829 | docs/standards/07-TEST-CASES.md |
| 8 | V&V Report | IEEE 1012 | docs/standards/08-VV-REPORT.md |
| 9 | EU AI Act Article-mapping | EU AI Act + harmonised standards | docs/standards/09-EU-AI-ACT-MAPPING.md |
| 10 | Risk Management Plan | Article 9 / ISO 31000 | docs/standards/10-RISK-MGMT-PLAN.md |
| 11 | Quality Management Plan | Article 17 / ISO 9001 | docs/standards/11-QUALITY-MGMT-PLAN.md |
| 12 | DPIA | GDPR Article 35 | docs/standards/12-DPIA.md |

Plus separate ADR folder: `docs/standards/adrs/0001-*.md` through `00NN-*.md` for
Architecture Decision Records (one per significant decision, MADR template).

### The 3 existing-MD rewrites (after the 12 are done)

- `README.md` - point at the new doc tree, summarise enterprise-readiness state
- `docs/ENTERPRISE-GAP-REGISTER.md` - re-cross-reference each gap against an SRS NFR
  ID so gap closure has a traceable target
- `docs/PROJECT_STATUS.md` - prune operational log entries; refer to the standards
  docs for canonical product state

### The test re-tagging task (after the test docs land)

- Add TC-XXXX tag to existing pytest tests via marker/decorator (NOT renaming)
  e.g. `@pytest.mark.tc("TC-0017")` or marker config in pytest.ini
- Add TC-XXXX tag to vitest tests via test name suffix
- Add TC-XXXX tag to Playwright spec test IDs
- Result: every test reports its TC ID in output, RTM link-check script can verify
  every TC mentioned in RTM exists in the actual test suite

---

## Page split

Phase-15 is large enough to split into 7 sub-pages (one per doc cluster) so each
page has a clean session boundary, fits in one chat context, and produces one
commit cluster.

| Page | Sub-phase | Docs produced | Est |
|------|-----------|---------------|-----|
| Page-003 | 15a Architecture | SAD + ADRs (top 10-15 decisions made through Phase 14) | 3-4 days |
| Page-004 | 15b Requirements | PRD + SRS (numbered FRs + NFRs) | 3-4 days |
| Page-005 | 15c Design | SDD (module + data model + API contracts) | 2-3 days |
| Page-006 | 15d Traceability | RTM + automated link-check script | 3-4 days |
| Page-007 | 15e Tests | Test Plan + Test Cases + V&V Report + test re-tagging | 3-4 days |
| Page-008 | 15f Compliance | EU AI Act mapping + Risk Mgmt + Quality Mgmt + DPIA | 3-4 days |
| Page-009 | 15g Cleanup | Existing-MD rewrites (README + GAP-REGISTER + PROJECT_STATUS) | 1-2 days |

**Total estimated effort:** 3-4 weeks at honest pace (PHASE-14 evidence rate).
**Total estimated effort:** 2-3 weeks if I tighten up significantly.

Each sub-page closes with the standard SESSION CLOSE CHECKLIST: backup PROJECT_STATUS,
update PROJECT_STATUS, write PHASE-15a-HANDOFF, write PHASE-15b-BUILD, final commit,
push.

---

## Doc structure conventions

- All standards docs live in `docs/standards/` to keep them clearly separated from
  PHASE-N-* operational handoffs and ENTERPRISE-GAP-REGISTER.md
- Numbered prefix (01-..12-) for ordering when listed alphabetically
- Each doc starts with: scope, standards referenced, document control table
  (version, date, author, reviewers, status)
- All cross-doc references use stable IDs: FR-XXX, NFR-XXX, ADR-XXXX, TC-XXXX,
  RISK-XXX, GAP-XX
- Every doc footer: "Last updated [DATE] | Phase: [PHASE-X] | Commit: [HASH]"
- Diagrams embedded as Mermaid (renders in GitHub) wherever possible, else PNG/SVG
  in `docs/standards/diagrams/`

## Required content per doc - bullet sketch

### 01-VISION-PRD
- Product vision, problem statement, target user personas (5 from PROJECT_STATUS),
  competitive landscape, success criteria, scope IN/OUT, assumptions, constraints

### 02-SRS
- FR-XXX functional requirements grouped by feature area:
  - FR-1xx submission pipeline, FR-2xx executor, FR-3xx review panel,
    FR-4xx Article 14 HIL, FR-5xx Vertex consensus, FR-6xx reporting,
    FR-7xx audit trail, FR-8xx multi-tenancy (future)
- NFR-XXX non-functional: NFR-1xx security, 2xx perf, 3xx availability,
  4xx compliance (EU AI Act + GDPR), 5xx maintainability
- Each requirement: ID, title, description, source (Article ref / market need /
  enterprise gap), acceptance criteria, priority (MUST/SHOULD/COULD/WONT)

### 03-SAD (arc42 template)
1. Introduction & goals
2. Architecture constraints
3. System scope & context (C4 Level 1: Context diagram)
4. Solution strategy
5. Building block view (C4 Level 2: Container diagram + Level 3: Component)
6. Runtime view (sequence diagrams for: submit task, BFT consensus, HIL flow, sign+verify)
7. Deployment view (Docker Compose topology, prod target topology)
8. Cross-cutting concepts (security, audit immutability, error handling)
9. Architecture decisions (links to ADRs)
10. Quality requirements (links to NFRs)
11. Risks & technical debt (links to ENTERPRISE-GAP-REGISTER)
12. Glossary

### ADRs (initial set, ~10-15)
- ADR-0001 Use FastAPI not Django
- ADR-0002 Use Celery + Redis for background jobs not RQ or Dramatiq
- ADR-0003 PostgreSQL trigger-enforced append-only audit_events
- ADR-0004 BFT consensus via FoxMQ (LIVE) with deterministic stub fallback
- ADR-0005 3-reviewer LLM panel with commitment-reveal pattern
- ADR-0006 HMAC-SHA256 signing (Phase 1) - MIGRATE to Ed25519 (per ADR-0014)
- ADR-0007 EU AI Act Articles as first-class JSON schema keys
- ADR-0008 Article 14 N-of-M quorum policy per task type
- ADR-0009 schema_version 1.1 with human_decisions_hash for tamper-evidence
- ADR-0010 React + Zustand (not Redux/Context) for frontend state
- ADR-0011 Playwright for E2E (not Cypress) - record demo videos in same tooling
- ADR-0012 Test pyramid: 100% coverage targets via pytest + vitest, E2E via Playwright
- ADR-0013 docs/standards/ tree introduced PHASE-15 (this ADR documents the meta-decision)
- ADR-0014 [PROPOSED] Migrate to Ed25519 / ECDSA P-256 - rationale: trustless verification
- ADR-0015 [PROPOSED] WORM storage / RFC-3161 anchoring for audit_events tamper-evidence

### 04-SDD
- For each container in SAD: module list, public interface, data model
- API contract: re-derive OpenAPI 3.0 spec from FastAPI routers, freeze in docs
- Data model: ERD for postgres tables (10 tables), JSON schemas for audit_events
  payloads, JSON schemas for signed report bundle
- Sequence diagrams for the 4 critical flows (submit, BFT, HIL, sign+verify)

### 05-RTM
- Spreadsheet-style table (markdown table or .csv) with columns:
  FR/NFR ID | Description | SRS ref | SDD ref | Code module(s) | Test case(s) | Status
- Status values: NOT_IMPLEMENTED, IMPLEMENTED, TESTED, VERIFIED
- Plus reverse-direction view: Test ID → Requirement ID
- Plus automated link-check script: parses RTM, ensures every TC-XXXX referenced
  exists in actual test suite, fails CI if not

### 06-TEST-PLAN
- Test strategy: unit + integration + E2E + property-based + load + security
- Coverage targets: 100% line on policy modules, 100% on API endpoints, 80% overall
- Test environment matrix: local docker, CI runner, demo recording host
- Defect classification: SEVERITY-1..4 + RESOLUTION categories

### 07-TEST-CASES
- Existing 565 backend + 109 frontend + 14 Playwright = 688 test cases get TC-XXXX
- Each TC entry: ID, title, type (unit/integration/E2E), preconditions, steps,
  expected result, requirement(s) covered (FR-/NFR-), test file path, line number
- Format: 1 row per test case in a structured markdown table or YAML file

### 08-VV-REPORT
- Evidence each numbered requirement is verified by passing tests
- Generated automatically from RTM + latest test run results
- Includes: total requirements, % verified, list of unverified requirements,
  list of orphan tests (test exists but no requirement)
- Run-script: `scripts/generate_vv_report.py` consumes RTM + pytest/vitest/playwright
  JSON outputs, produces docs/standards/08-VV-REPORT.md

### 09-EU-AI-ACT-MAPPING
- Per Article (9, 13, 14, 17), structured table:
  Article clause | Verbatim text | Auditex feature(s) | Audit field(s) | Test case(s) |
  Legal review status (PENDING/REVIEWED-BY-X-ON-DATE)
- Caveat at top: engineer-authored draft; barrister review pending (per Gap 8)
- Cross-link to FR-/NFR- IDs in SRS

### 10-RISK-MGMT-PLAN (Article 9 / ISO 31000)
- Risk identification: enumerate AI risks per task type (contract_check,
  risk_analysis, document_review)
- Risk assessment: likelihood × impact matrix
- Risk treatment: mitigations in Auditex (BFT consensus, Article 14 HIL,
  audit trail, sign+verify)
- Monitoring: continuous (audit_events stream), periodic (reviewer benchmark)
- Risk register table: ID, description, likelihood, impact, mitigation, owner, status

### 11-QUALITY-MGMT-PLAN (Article 17 / ISO 9001)
- Process: how features are designed, implemented, tested, released
- Change control: ADR process, gap-register updates, RTM resync
- Defect management: SEVERITY classification, response SLA, postmortem template
- Continuous improvement: metrics, review cadence
- Roles & responsibilities (today: solo founder; future: per Auditex submission deck)

### 12-DPIA (GDPR Article 35)
- Data flow diagram: customer doc → API → PostgreSQL → Anthropic + OpenAI APIs →
  back to PostgreSQL → audit chain → signed report → customer download
- Data categories: personal data fields per task type, inferred attributes
- Lawful basis assessment per category
- Risk analysis: re-identification, third-party transfer, retention
- Mitigations: in-product (PII redaction option future), contractual (DPA template),
  technical (encryption at rest + transit)
- Caveat at top: engineer-authored draft; DPO review pending (per Gap 7)

---

## Standing rules in effect for all 7 sub-pages

- **ops.ps1 is the ONLY way to run operations.** PHASE-13/14 waiver expired.
  No raw shell unless user explicitly re-grants.
- **FILE BACKUP RULE:** backup before edit/delete with `_backup\FILENAME_YYYYMMDD-HHMM.ext`,
  byte-for-byte verbatim, hash-verified.
- **Plan-first BEHAVIOUR RULE:** show plan, get approval, then act.
- **Read logs from `runs/ops_*.log` directly** via filesystem MCP. Never ask user to paste.
- **Warn at ~50% context.**
- **Auditex uses `docs/PHASE-N-*` and `docs/standards/*` conventions.** No context_log/.
- **Plan + commit per doc**, not per page. Each completed standards doc gets its
  own commit so RTM and V&V can be reproduced from any commit hash.
- **No file deletion without archive** per the audit-trail principle (you flagged
  this in PHASE-14: deleting our own work history contradicts the product thesis).
  When a doc is superseded, move to `docs/_archive/` not delete.

---

## Next session start

Read this file. Then read `docs/PROJECT_STATUS.md` for current state. Begin with
**Page-003 / Sub-phase 15a Architecture**: SAD + ADRs.

Open the SAD with the arc42 outline above. Walk through each section and either
write content or write `[TODO Page-003: ...]` placeholders. Goal of Page-003 is
a complete-enough SAD that a senior engineer reading cold understands the system,
plus the first 10-15 ADRs documenting decisions already made.

After Page-003 closes: HEAD has SAD + ADRs committed, PROJECT_STATUS.md updated,
PHASE-15a-HANDOFF written, PHASE-15b-BUILD-PROMPT written.

---

## Honest expectations for this phase

This is reference work, not user-visible feature work. Three weeks of doc writing
will produce no demo improvement, no new test, no shipped feature. What it produces
is the ability to credibly answer:

- "Show me your SRS for FR-042" → here, with traceability to the test that proves it
- "Where is the architecture decision for the 3-reviewer panel" → ADR-0005
- "How does this comply with EU AI Act Article 14" → 09-EU-AI-ACT-MAPPING.md row 14.x
- "Is there a DPIA" → 12-DPIA.md (engineer draft pending DPO review)
- "Show me your test plan" → 06-TEST-PLAN.md

That ability is what unlocks the next funding tranche conversation, the first paid
pilot, the SOC 2 readiness consultation, the legal Article-mapping review.

The risk is doing all this without a buyer in the loop, optimising for an imagined
procurement bar instead of a real one. Mitigation: keep ENTERPRISE-GAP-REGISTER.md
honest, time-box each sub-page strictly, and pause for a design-partner conversation
between sub-pages if any becomes available.

---

**End of PHASE-15 build prompt.**
