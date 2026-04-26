# PHASE-15 Build Prompt — Full Enterprise Doc Superset (50+ docs)

**Phase:** PHASE-15 - Complete enterprise documentation spine across all 8 layers (Business, User/Process, Product/Functional, Architecture/Design, Security/Risk/Compliance, Operations/Quality, Project/Process, Traceability)
**Trigger:** PHASE-14 video shipped to DoraHacks 27/04/2026. Project pivots from hackathon-grade to full enterprise-procurement-ready doc spine.
**HEAD at start:** e0b6d5b (Phase-14 close + Phase-15 plan v2)
**Branch:** main (doc work is reversible reference material; demo state untouched)
**Next session:** Read this file first.

---

## Why this phase exists (rationale)

Auditex shipped a working POC + Article 14 + 6-scenario demo on DoraHacks BUIDL #43345.
Industry-standard enterprise procurement requires a documentation spine that today does
not exist. Without it, no regulated-industry buyer (banking / defence / healthcare /
EU AI Act-affected) can complete a security questionnaire, RFP, or procurement gate.

PHASE-15 produces the **full superset** of enterprise documentation across all 8 layers
of the IEEE / ISO / arc42 / Indian-IT-HLD-LLD / RUP / NIST AI RMF / EU AI Act / GDPR
combined doc taxonomy. ~50+ documents total.

This is reference work. No new features. No demo improvement. What it produces is the
ability to credibly answer ANY enterprise procurement question with a numbered document
ID, traceable from business need to design to test to evidence.

After PHASE-15, future code changes update the relevant doc(s) as part of the change.
Engineering resumes at PHASE-16 with this spine in place.

---

## Honest expectations

- **Scope:** ~50+ docs across 8 layers
- **Effort at honest pace:** 2-3 months solo
- **Effort if tightened:** 6-8 weeks
- **Page count:** 10-12 sub-pages within PHASE-15 (one per layer + cross-cutting layers)
- **Risk acknowledged:** doc-without-buyer optimises for imagined enterprise; mitigation
  is to keep ENTERPRISE-GAP-REGISTER.md honest and pause for design-partner conversation
  between sub-pages whenever one becomes available

---

## The full doc list - 50+ items across 8 layers

All docs live under `docs/standards/` with numbered prefix folders for ordering.
Doc IDs are stable identifiers used in cross-references (e.g. RTM links FR-042 →
HLD-§4.2 → LLD-§7.1 → TC-0173).

### Layer 1 - Business / Commercial (4 docs) — `docs/standards/01-business/`

| Doc ID | Document | Standard / AKA | Purpose |
|--------|----------|----------------|---------|
| BUS-01 | Vision & Mission Statement | — | Why the company exists; 5-year vision |
| BUS-02 | BRD - Business Requirements Document | Business Case | Business objectives, ROI, stakeholder needs |
| BUS-03 | MRD - Market Requirements Document | — | Market need, competitive landscape, sizing, TAM/SAM/SOM |
| BUS-04 | ConOps - Concept of Operations | — | How users operate the system in their world |

### Layer 2 - User / Process (5 docs) — `docs/standards/02-user/`

| Doc ID | Document | Standard / AKA | Purpose |
|--------|----------|----------------|---------|
| USR-01 | User Personas | — | Aoife O'Connor, Marcus Whitaker, Klaus Reuter, Sophie Lambert, Elena Costa (5 personas already in PROJECT_STATUS) |
| USR-02 | Use Cases | UC-XXX, IEEE/UML | Actor + main flow + alt flows + exception flows |
| USR-03 | User Journey Maps | — | Persona-on-timeline visual per persona |
| USR-04 | User Stories Backlog | Agile epics | "As [actor] I want [goal] so that [outcome]" - epic-level, derived from use cases |
| USR-05 | BPMN Process Flow Diagrams | BPMN 2.0 | End-to-end business processes the product fits into (e.g. compliance review workflow) |

### Layer 3 - Product / Functional (5 docs) — `docs/standards/03-product/`

| Doc ID | Document | Standard / AKA | Purpose |
|--------|----------|----------------|---------|
| PRD-01 | PRD - Product Requirements Document | — | Product vision, scope, features, success criteria |
| FRS-01 | FRS - Functional Requirements Specification | IEEE 830 | What the system must DO (FR-001..N), grouped by feature area |
| NFR-01 | NFR Specification | IEEE 830 | Non-functional reqs (NFR-001..N): security, perf, availability, compliance, maintainability |
| SRS-01 | SRS - Software Requirements Specification | IEEE 830 / ISO 29148 | Combined FR + NFR; the canonical requirements doc |
| ACR-01 | Acceptance Criteria | A/C | Pass/fail criteria per requirement, used by test cases |

### Layer 4 - Architecture / Design (11 docs) — `docs/standards/04-architecture/`

| Doc ID | Document | Standard / AKA | Purpose |
|--------|----------|----------------|---------|
| HLD-01 | HLD - High-Level Design | Indian IT / SAD-equiv | Components, containers, deployment, integration patterns |
| LLD-01 | LLD - Low-Level Design | Indian IT / SDD-equiv | Module internals, classes, sequence, pseudo-code |
| SAD-01 | SAD - Software Architecture Document | ISO 42010 / arc42 / C4 | Western/IEEE name for HLD-equivalent (cross-references HLD) |
| SDD-01 | SDD - Software Design Document | IEEE 1016 | Detailed module design (cross-references LLD) |
| TDD-01 | TDD - Technical Design Document | — | Combined HLD + LLD walkthrough for technical-buyer review |
| API-01 | API Specification | OpenAPI 3.0 / Swagger | Standalone API contract derived from FastAPI routers |
| DM-01 | Data Model / ERD | — | DB schema diagrams + per-table descriptions |
| DD-01 | Data Dictionary | DD | Every field semantic + type + constraints + example values |
| ICD-01 | Interface Control Document | ICD | External interfaces (Anthropic API, OpenAI API, FoxMQ, postgres, redis) |
| SLN-01 | Solution Architecture Document | — | Cross-cutting view (architecture + ops + security combined) |
| ADR-XXXX | Architecture Decision Records | MADR | One file per decision (~15-20 records initial) |

### Layer 5 - Security / Risk / Compliance (11 docs) — `docs/standards/05-security-risk-compliance/`

| Doc ID | Document | Standard / AKA | Purpose |
|--------|----------|----------------|---------|
| THR-01 | Threat Model | STRIDE / DREAD / PASTA | Attack surface analysis, per-component threats |
| SEC-01 | Security Architecture Document | SAD-Sec | Controls, encryption, key management, secret rotation |
| SRS-SEC-01 | Security Requirements Specification | — | NFR-Sec subset extracted as standalone for security review |
| RMP-01 | Risk Management Plan | ISO 31000 / Article 9 | Process for identifying / assessing / treating / monitoring risks |
| RR-01 | Risk Register | — | Live tracking spreadsheet of identified risks |
| DPIA-01 | DPIA - Data Protection Impact Assessment | GDPR Article 35 | Privacy risk per data flow |
| PIA-01 | PIA - Privacy Impact Assessment | — | Non-EU jurisdictions; often = DPIA |
| CONF-01 | EU AI Act Conformity Assessment | EU AI Act + harmonised standards | Article-by-article evidence (Articles 9, 13, 14, 17 covered today; 5, 8, 10, 11, 12, 15, 16 future) |
| AIRMF-01 | AI Risk Management Plan | NIST AI RMF | AI-specific risks (model drift, hallucination, prompt injection, bias) |
| MOD-XX | Model Cards | — | Per-LLM-model spec sheet (Claude Sonnet, GPT-4o, etc): vendor / version / training cutoff / known limits / use restrictions |
| BIAS-01 | Bias / Fairness Assessment | NIST AI RMF / Algorithmic Accountability | Disparate impact analysis across protected attributes |

### Layer 6 - Operations / Quality (12 docs) — `docs/standards/06-operations-quality/`

| Doc ID | Document | Standard / AKA | Purpose |
|--------|----------|----------------|---------|
| QMP-01 | Quality Management Plan | ISO 9001 / Article 17 | Process, change control, defect management |
| TS-01 | Test Strategy | — | Overall testing approach (unit/integration/E2E/property/load/security) |
| TP-01 | Test Plan | IEEE 829 | Specific test plan per release / per phase |
| TC-XXXX | Test Cases | IEEE 829 | Numbered cases (TC-0001..NNNN) linked to requirements |
| TDM-01 | Test Data Management Plan | — | Synthetic / anonymised data sources, refresh cadence |
| VVP-01 | V&V Plan | IEEE 1012 | Verification + validation activity schedule |
| VVR-01 | V&V Report | IEEE 1012 | Evidence each requirement verified by passing tests (auto-generated) |
| DMP-01 | Defect Management Plan | — | Severity classification, response SLA, escalation, postmortem template |
| OPS-01 | Operations Runbook | Ops Manual | How to run the system day-to-day (extends current docs/OPS-RUNBOOK.md) |
| DRP-01 | Disaster Recovery Plan | DRP | RTO/RPO + procedures + drills |
| BCP-01 | Business Continuity Plan | BCP | Above DR; people + process continuity |
| CAP-01 | Capacity Plan | — | Load characteristics, scaling triggers, capacity targets |
| PERF-01 | Performance Plan | — | SLO / SLA definitions, perf budgets per endpoint |
| MON-01 | Monitoring + Observability Plan | — | Metrics, alerts, dashboards, on-call rotation |
| IRP-01 | Incident Response Plan | IRP | When things break: detection → response → resolution → review |

(Layer 6 is 15 docs; counted 12 above and added 3 — corrected total below.)

### Layer 7 - Project / Process (8 docs) — `docs/standards/07-project-process/`

| Doc ID | Document | Standard / AKA | Purpose |
|--------|----------|----------------|---------|
| CHTR-01 | Project Charter | — | Authorization + scope (lighter for solo founder; reads as company charter) |
| PMP-01 | Project Management Plan | PMP | Schedule, budget, resources |
| WBS-01 | WBS - Work Breakdown Structure | — | Task decomposition |
| RACI-01 | RACI Matrix | — | Responsible / Accountable / Consulted / Informed across roles |
| STK-01 | Stakeholder Register | — | Who cares + why + influence/interest grid |
| COMM-01 | Communication Plan | — | Who gets which updates, when, how |
| CMP-01 | Change Management Plan | — | How changes are proposed, reviewed, approved, deployed |
| GLOSS-01 | Glossary / Ontology | — | Domain term definitions (EU AI Act + Auditex specific) |
| REF-01 | References / Bibliography | — | External standards cited + version numbers |

(Layer 7 is 9 docs; corrected total below.)

### Layer 8 - Traceability / Cross-cutting (3 docs) — `docs/standards/08-traceability/`

| Doc ID | Document | Standard / AKA | Purpose |
|--------|----------|----------------|---------|
| RTM-01 | RTM - Requirements Traceability Matrix | — | BRD → SRS (FR/NFR) → HLD → LLD → Code module → Test case → V&V evidence |
| COMP-01 | Compliance Matrix | — | Regulation (EU AI Act / GDPR / ISO 27001 future / SOC 2 future) → Auditex feature → Test evidence |
| COV-01 | Coverage Report | — | Test coverage % per requirement, auto-generated from RTM + test results |

---

## Correct total count

- Layer 1 Business: 4
- Layer 2 User/Process: 5
- Layer 3 Product/Functional: 5
- Layer 4 Architecture/Design: 11 (counting ADRs as 1 doc family)
- Layer 5 Security/Risk/Compliance: 11
- Layer 6 Operations/Quality: 15 (corrected)
- Layer 7 Project/Process: 9 (corrected)
- Layer 8 Traceability: 3
- **Plus existing-MD rewrites:** README, ENTERPRISE-GAP-REGISTER, PROJECT_STATUS = 3
- **Plus existing-MD audit:** OPS-RUNBOOK, MEMORY, all docs in docs/api/, docs/architecture/,
  docs/compliance/, docs/testing/ = need review and either retain/merge/archive

**Grand total: 63 standards docs + 3 existing rewrites + audit pass over current docs/ tree.**

(Earlier statement of "50+" was conservative; full superset is closer to 63.)

---

## Page split - 12 sub-pages within PHASE-15

To keep each session focused and produce a clean commit cluster per session, PHASE-15
splits across 12 sub-pages. Each sub-page closes with the SESSION CLOSE CHECKLIST
(backup PROJECT_STATUS, update PROJECT_STATUS, write PHASE-15X-HANDOFF, write
PHASE-15Y-BUILD, final commit, push).

| Page | Sub-phase | Layer + docs | Est days (honest) |
|------|-----------|--------------|-------------------|
| Page-003 | 15a Business | Layer 1 (BUS-01 to BUS-04) - 4 docs | 2-3 |
| Page-004 | 15b User/Process | Layer 2 (USR-01 to USR-05) - 5 docs | 3-4 |
| Page-005 | 15c Product/Functional | Layer 3 (PRD/FRS/NFR/SRS/ACR) - 5 docs | 3-4 |
| Page-006 | 15d HLD + Architecture | Layer 4 part 1: HLD-01, SAD-01, ADR-XXXX (15-20 ADRs), ICD-01, SLN-01 | 4-5 |
| Page-007 | 15e LLD + Detailed Design | Layer 4 part 2: LLD-01, SDD-01, TDD-01, API-01, DM-01, DD-01 | 4-5 |
| Page-008 | 15f Security + Risk | Layer 5 part 1: THR-01, SEC-01, SRS-SEC-01, RMP-01, RR-01 | 3-4 |
| Page-009 | 15g Privacy + AI Compliance | Layer 5 part 2: DPIA-01, PIA-01, CONF-01, AIRMF-01, MOD-XX (per-model cards), BIAS-01 | 3-4 |
| Page-010 | 15h Quality + Test Docs | Layer 6 part 1: QMP-01, TS-01, TP-01, TC-XXXX (688 test cases tagged), TDM-01, VVP-01, VVR-01, DMP-01 | 5-6 |
| Page-011 | 15i Ops + Resilience | Layer 6 part 2: OPS-01, DRP-01, BCP-01, CAP-01, PERF-01, MON-01, IRP-01 | 3-4 |
| Page-012 | 15j Project Process | Layer 7 (CHTR/PMP/WBS/RACI/STK/COMM/CMP/GLOSS/REF) - 9 docs | 2-3 |
| Page-013 | 15k Traceability | Layer 8 (RTM/COMP/COV) + automated link-check script + V&V auto-generator | 4-5 |
| Page-014 | 15l Cleanup + Audit | Existing-MD rewrites (README/GAP-REGISTER/PROJECT_STATUS) + audit pass over docs/ tree | 2-3 |

**Total estimated effort:** 38-50 days at honest pace = ~6-10 weeks of focused work.

---

## Standing rules in effect for all 12 sub-pages

- **ops.ps1 is the ONLY way to run operations.** PHASE-13/14 waiver expired.
  No raw shell unless user explicitly re-grants per page.
- **FILE BACKUP RULE:** backup before edit/delete with `_backup\FILENAME_YYYYMMDD-HHMM.ext`,
  byte-for-byte verbatim, hash-verified.
- **NO-DELETION ARCHIVAL RULE** (per Senthil PHASE-14 audit-trail principle):
  superseded docs go to `docs/_archive/` with a redirect note in the new location.
  Never `rm` historical work.
- **Plan-first BEHAVIOUR RULE:** show plan, get approval, then act.
- **Read logs from `runs/ops_*.log` directly** via filesystem MCP. Never ask user to paste.
- **Warn at ~50% context.**
- **Auditex uses `docs/PHASE-N-*` and `docs/standards/NN-LAYER/*` conventions.**
  No context_log/. No CSR jargon.
- **Plan + commit per doc**, not per page. Each completed standards doc gets its own
  commit so RTM and V&V can be reproduced from any commit hash.

---

## Doc structure conventions (applies to every doc)

- Lives under `docs/standards/0X-LAYER-NAME/` with numbered prefix
- Markdown format primary; OpenAPI YAML for API-01; .csv or markdown table for RTM-01
- First section: **Document control table** (version, date, author, reviewers,
  status: DRAFT / IN-REVIEW / APPROVED / SUPERSEDED, related docs)
- Second section: **Scope + standards referenced**
- Third section: **Definitions & terms** (cross-link to GLOSS-01)
- Body: per-doc structure based on standard
- Footer: "Last updated [DATE] | Phase: PHASE-15X | Commit: [HASH] | Supersedes: [PRIOR DOC if any]"
- Diagrams: Mermaid embedded where possible (renders in GitHub), else PNG/SVG in
  `docs/standards/_diagrams/` with source files (e.g. .drawio) checked in
- All cross-doc references use stable IDs: BUS-NN, USR-NN, FR-NNNN, NFR-NNNN,
  ADR-XXXX, HLD-§X.X, LLD-§X.X, TC-XXXX, RISK-NNN, GAP-NN

---

## Per-layer detailed content sketch (high level only - each sub-page expands its own)

### Layer 1 - Business / Commercial

**BUS-01 Vision & Mission**
- 5-year vision: be the de-facto cryptographic audit trail for AI-assisted decisions
  in regulated industries
- Mission: every AI decision provably auditable, third-party verifiable, with human
  oversight per Article 14
- Values: honesty (gap register), transparency (audit-by-design), engineering rigor
  (100% coverage)

**BUS-02 BRD - Business Requirements Document**
- Business problem: 7% global revenue EU AI Act fines, no audit primitive exists
- Stakeholders: CISO, Compliance Officer, Risk Officer, AI Lead, Procurement, Legal
- Business objectives: 5 paid pilots in year 1, GBP 250K ARR by month 12
- Investment summary: 4-tranche funding plan from AUDITEX-DORAHACKS-SUBMISSION
- ROI: regulatory penalty avoidance × probability + insurance premium reduction
- Success criteria + measurement
- Cross-link to MRD-01 for market validation

**BUS-03 MRD - Market Requirements Document**
- TAM: EU companies subject to AI Act high-risk obligations
- SAM: regulated industries (banking + defence + healthcare + insurance)
- SOM: UK-EU adjacent companies in 2026-2028 enforcement window
- Competitive landscape: Credo AI, Holistic AI, Fiddler, Arize, native Anthropic/OpenAI
- Differentiation matrix
- Pricing strategy hypothesis (per-audit vs per-seat vs hybrid)

**BUS-04 ConOps - Concept of Operations**
- "A day in the life" for each persona
- Workflows: ad-hoc audit, scheduled audit, escalation review, regulatory submission
- Operational environment: cloud SaaS today, on-prem appliance future

### Layer 2 - User / Process

**USR-01 User Personas** (5 personas already in PROJECT_STATUS):
- Aoife O'Connor (Compliance Officer, Mid-tier UK fintech)
- Marcus Whitaker (CISO, Defence contractor)
- Klaus Reuter (Risk Officer, German private bank)
- Sophie Lambert (Head of AI Governance, Healthcare)
- Elena Costa (EU AI Act Audit Manager, Big-4 advisory)

For each persona: demographics, goals, pain points, technology comfort, decision power,
typical day, success criteria, objections.

**USR-02 Use Cases** (UC-001..NN):
- UC-001 Submit task for compliance audit
- UC-002 Review AI consensus result
- UC-003 Provide human oversight decision (Article 14)
- UC-004 Configure oversight policy per task type
- UC-005 Export signed compliance report
- UC-006 Verify report signature offline (third-party)
- UC-007 View audit trail for a task
- UC-008 Manage API keys (future multi-tenancy)
- UC-009 Manage user roles (future RBAC)
- UC-010 Investigate failed task (DLQ)
- UC-011 Replay task from audit log
- UC-012 Generate periodic compliance report
- UC-013 Respond to regulator audit request
- UC-014 Onboard new compliance reviewer
- UC-015 Review LLM-vs-human-auditor benchmark results

Each: Actor, preconditions, postconditions, main flow, alt flows, exception flows,
NFR refs, cross-link to FR-XXX in SRS.

**USR-03 User Journey Maps**: per-persona timeline visual (compliance officer's
quarterly cycle; CISO's annual procurement cycle; etc).

**USR-04 User Stories Backlog**: epic-level stories derived from use cases,
groomed for Agile sprint planning when team grows.

**USR-05 BPMN Process Flow Diagrams**:
- BP-01 End-to-end compliance audit process
- BP-02 Article 14 escalation workflow
- BP-03 Regulator audit response workflow
- BP-04 Internal model retraining + re-audit cycle

### Layer 3 - Product / Functional

**PRD-01 PRD** - rewrite of AUDITEX-DORAHACKS-SUBMISSION as proper product doc.

**FRS-01 FRS** - functional requirements grouped by feature area:
- FR-1xx Submission pipeline
- FR-2xx AI Executor
- FR-3xx Review Panel
- FR-4xx Article 14 HIL
- FR-5xx Vertex Consensus
- FR-6xx Reporting
- FR-7xx Audit Trail
- FR-8xx Multi-tenancy (future, BLOCKER #5)
- FR-9xx Crypto signing (future, BLOCKER #1)
- FR-10xx Observability (future)

**NFR-01 NFR Spec**:
- NFR-1xx Security (encryption at rest/transit, key rotation, access control)
- NFR-2xx Performance (latency budgets per endpoint, throughput, cost-per-audit)
- NFR-3xx Availability (uptime targets, RTO/RPO)
- NFR-4xx Compliance (EU AI Act, GDPR, future SOC 2, ISO 27001)
- NFR-5xx Maintainability (test coverage, doc sync, code quality gates)

**SRS-01 SRS** = combined FR + NFR canonical doc.

**ACR-01 Acceptance Criteria**: pass/fail per requirement, used by test cases.

### Layer 4 - Architecture / Design

**HLD-01** - components, containers, deployment, integration patterns.
Indian-IT-style readable for technical buyer review.

**LLD-01** - module internals, classes, sequence diagrams per critical flow.
Implementation-engineer readable.

**SAD-01** - arc42 / C4 model: context (L1), container (L2), component (L3), code (L4).
Western/IEEE-readable.

**SDD-01** - IEEE 1016 module design.

**TDD-01** - combined HLD+LLD walkthrough.

**API-01** - OpenAPI 3.0 derived from FastAPI routers, frozen as standalone artifact.

**DM-01 Data Model** - ERD for 10 postgres tables + JSON schemas for audit_events
payloads + JSON schemas for signed report bundle.

**DD-01 Data Dictionary** - every field semantic + type + constraints + example
across all 10 tables and all JSON schemas.

**ICD-01 Interface Control Document** - external interfaces:
- Anthropic API (auth, rate limits, retry, fallback)
- OpenAI API (same)
- FoxMQ broker (LIVE BFT mode + STUB fallback)
- PostgreSQL (connection pooling, RLS future)
- Redis (rate limit, API key cache, Celery broker)

**SLN-01 Solution Architecture** - cross-cutting view combining architecture, ops, security.

**ADRs** (initial set 15-20):
- ADR-0001 Use FastAPI not Django
- ADR-0002 Celery + Redis (not RQ / Dramatiq)
- ADR-0003 PostgreSQL trigger-enforced append-only audit_events
- ADR-0004 BFT consensus via FoxMQ LIVE with STUB fallback
- ADR-0005 3-reviewer LLM panel with commitment-reveal pattern
- ADR-0006 HMAC-SHA256 signing (Phase 1) - to be migrated per ADR-0014
- ADR-0007 EU AI Act Articles as first-class JSON schema keys
- ADR-0008 Article 14 N-of-M quorum policy per task type
- ADR-0009 schema_version 1.1 with human_decisions_hash for tamper-evidence
- ADR-0010 React + Zustand (not Redux/Context)
- ADR-0011 Playwright for E2E (not Cypress) - record demos in same tooling
- ADR-0012 Test pyramid: 100% coverage targets
- ADR-0013 docs/standards/ tree introduced PHASE-15
- ADR-0014 [PROPOSED] Migrate to Ed25519 / ECDSA P-256
- ADR-0015 [PROPOSED] WORM storage / RFC-3161 anchoring for audit_events
- ADR-0016 [PROPOSED] Multi-tenancy via postgres RLS (alternative: per-org schemas)
- ADR-0017 [PROPOSED] OAuth 2.0 + OIDC for SSO (alternative: SAML 2.0)
- ADR-0018 [PROPOSED] Per-model adapter pattern for multi-LLM-provider support
- ADR-0019 [PROPOSED] Notary / Merkle root anchoring cadence
- ADR-0020 [PROPOSED] On-prem deployment topology (air-gapped + bring-your-own-LLM)

### Layer 5 - Security / Risk / Compliance

**THR-01 Threat Model** - STRIDE per component:
- API gateway: Spoofing (API key compromise), Tampering (request injection), Repudiation
  (already addressed via audit chain), Info disclosure, DoS (rate limiter), Elevation
- Worker: prompt injection in user input, LLM API compromise
- Storage: postgres compromise, redis compromise, backup compromise
- External LLM: data exfiltration via prompts, response tampering
DREAD scoring per threat. Mitigations table cross-links to NFRs.

**SEC-01 Security Architecture** - controls per CIS / NIST CSF / ISO 27002:
- Identity & access (today: shared API key; future: per-org keys + RBAC + SSO)
- Cryptography (today: HMAC-SHA256; future: Ed25519)
- Data protection (encryption at rest in postgres, in transit via TLS)
- Logging & monitoring (audit_events + future Prometheus + structured logs)
- Incident response (cross-link to IRP-01)

**SRS-SEC-01 Security Requirements Spec** - NFR-Sec extracted as standalone for
external security review.

**RMP-01 Risk Management Plan** - ISO 31000 process: identify, assess, treat, monitor.

**RR-01 Risk Register** - live spreadsheet:
- RISK-001 LLM API outage
- RISK-002 Prompt injection in user docs
- RISK-003 Postgres compromise
- RISK-004 HMAC key leak
- RISK-005 Reviewer correlation (3 LLMs not independent)
- RISK-006 EU AI Act enforcement softening
- RISK-007 Anthropic / OpenAI native audit mode launch
- RISK-008 Solo founder velocity ceiling
- RISK-009 Regulator rejects LLM verdicts
- RISK-010 Cost-per-audit blowout via LLM API price increase
[continue per ENTERPRISE-GAP-REGISTER + SWOT threats]

**DPIA-01** - GDPR Art 35 privacy risk per data flow.

**PIA-01** - non-EU jurisdictions equivalent.

**CONF-01 EU AI Act Conformity Assessment** - Article-by-article evidence:
- Art 9 (Risk Mgmt) - cross-link to RMP-01 + RR-01 + Auditex risk fields
- Art 13 (Transparency) - cross-link to PRD + plain-English summary feature
- Art 14 (Human Oversight) - cross-link to HIL implementation + USR-02 UC-003/004
- Art 17 (Quality Mgmt) - cross-link to QMP-01
- Art 5, 8, 10, 11, 12, 15, 16 - flag as NOT-YET-IMPLEMENTED with roadmap
Caveat at top: engineer-authored draft, barrister review pending (per Gap 8).

**AIRMF-01 AI Risk Management Plan** - NIST AI RMF GOVERN/MAP/MEASURE/MANAGE per
function. AI-specific risks (drift, hallucination, prompt injection, bias).

**MOD-XX Model Cards** - per LLM:
- MOD-01 Claude Sonnet (vendor, version, training cutoff, context window, known limits,
  use restrictions)
- MOD-02 GPT-4o
- MOD-03 GPT-4o (second instance for reviewer)
- MOD-04 [Future] Gemini
- MOD-05 [Future] Llama / Mistral on-prem option

**BIAS-01 Bias / Fairness Assessment** - disparate impact analysis. Plan to run
benchmark against certified human auditors per Gap 4. Currently flagged as NOT-RUN.

### Layer 6 - Operations / Quality

**QMP-01** - ISO 9001 / Article 17. Process, change control, defect mgmt.

**TS-01 Test Strategy** - test pyramid, types, coverage targets.

**TP-01 Test Plan** - per-release test plan template.

**TC-XXXX Test Cases** - 688 existing tests tagged TC-0001..0688 via pytest markers /
vitest names / Playwright IDs. Each TC entry: ID, title, type, preconditions, steps,
expected, requirement(s) covered, file path, line.

**TDM-01 Test Data Management Plan** - synthetic data sources, refresh, anonymisation.

**VVP-01 V&V Plan** - schedule of verification + validation activities.

**VVR-01 V&V Report** - auto-generated from RTM + latest test run JSON outputs.

**DMP-01 Defect Management Plan** - severity, SLA, escalation, postmortem template.

**OPS-01 Operations Runbook** - extends current docs/OPS-RUNBOOK.md. Covers:
- Daily ops (start/stop services, view logs, tail audit_events)
- Monitoring (alerts, dashboards, on-call)
- Backup/restore
- Common incidents + recovery
- Maintenance windows

**DRP-01 Disaster Recovery Plan** - RTO/RPO targets, backup procedures, failover, drills.

**BCP-01 Business Continuity Plan** - above DR. People + process continuity.

**CAP-01 Capacity Plan** - load characteristics, scaling triggers per service, capacity
targets per pricing tier (future).

**PERF-01 Performance Plan** - SLO/SLA per endpoint, perf budgets, load test cadence.

**MON-01 Monitoring + Observability Plan** - metrics, alerts, dashboards, on-call rota.

**IRP-01 Incident Response Plan** - detection, triage, response, resolution, postmortem.

### Layer 7 - Project / Process

**CHTR-01 Project Charter** (lighter for solo founder; reads as company charter):
- Authority, scope, exclusions, milestones, success criteria

**PMP-01 Project Management Plan** - schedule, budget, resources.

**WBS-01 Work Breakdown Structure** - top-level packages to leaf tasks.

**RACI-01 RACI Matrix** - across roles for the typical activities.

**STK-01 Stakeholder Register** - influence/interest grid per stakeholder.

**COMM-01 Communication Plan** - update cadence per stakeholder.

**CMP-01 Change Management Plan** - ADR process, gap-register updates, RTM resync,
release process.

**GLOSS-01 Glossary / Ontology** - domain terms (EU AI Act, GDPR, BFT, Vertex consensus,
HMAC, Ed25519, etc).

**REF-01 References / Bibliography** - external standards cited with version numbers.

### Layer 8 - Traceability / Cross-cutting

**RTM-01 RTM** - master traceability spreadsheet:
- Columns: BRD ID | MRD ID | Use Case | FR/NFR | HLD §  | LLD §  | Code module | Test case | V&V status
- Rows: one per requirement
- Status: NOT_IMPLEMENTED / IMPLEMENTED / TESTED / VERIFIED
- Companion script `scripts/rtm_link_check.py`: parses RTM, ensures every TC-XXXX
  exists in actual test suite, ensures every code module referenced exists in repo,
  fails CI if not

**COMP-01 Compliance Matrix** - regulation → feature → evidence:
- EU AI Act Article → CONF-01 § → FR/NFR → Test case → Status
- GDPR Article → DPIA § → Feature → Status
- ISO 27001 control (future) → SEC-01 § → Status
- SOC 2 control (future) → SEC-01 § → Status

**COV-01 Coverage Report** - auto-generated from RTM + latest test outputs:
- % requirements verified
- Orphan tests (no requirement)
- Untested requirements
- Per-layer breakdown

---

## Existing-MD audit pass (Page-014 / 15l)

Walk through every existing markdown file under `docs/` and decide:
- **RETAIN AS-IS** - still canonical (e.g. PHASE-N-* operational handoffs)
- **MERGE INTO STANDARDS** - content folded into a new standards doc
- **ARCHIVE** - moved to `docs/_archive/` with redirect note
- **REWRITE** - kept name, content rewritten to align with new spine

Files known to need attention:
- `docs/README.md` (if exists) - point at standards tree
- `docs/PROJECT_STATUS.md` - prune operational log, point at canonical product state
  in standards docs
- `docs/ENTERPRISE-GAP-REGISTER.md` - cross-reference each gap to NFR ID
- `docs/MEMORY.md` - keep or archive
- `docs/OPS-RUNBOOK.md` - merge into OPS-01
- `docs/api/` - merge into API-01
- `docs/architecture/` - audit, may merge into HLD-01 / SAD-01
- `docs/compliance/` - audit, merge into Layer 5 docs
- `docs/testing/` - merge into TS-01 / TP-01
- `docs/PHASE-N-*.md` files - retain as operational handoffs (not standards)

---

## Done-criteria for PHASE-15

PHASE-15 is complete when:
1. All 63 standards docs exist under `docs/standards/0X-LAYER/` with version control table,
   scope, and stable IDs
2. RTM-01 is populated and `scripts/rtm_link_check.py` passes (every TC referenced
   exists in the test suite, every code module referenced exists in the repo)
3. VVR-01 is auto-generated and shows the verification status of every requirement
4. COMP-01 covers EU AI Act Articles 9/13/14/17 (others flagged as ROADMAP) and GDPR
5. All 688 existing tests carry their TC-XXXX tag
6. ENTERPRISE-GAP-REGISTER.md cross-references each gap to a NFR ID
7. README.md points at the standards tree
8. PROJECT_STATUS.md updated to reflect PHASE-15 close
9. PHASE-16-BUILD-PROMPT.md written for resumed engineering work (Ed25519, multi-tenancy,
   observability) with explicit doc-update obligations per code change

---

## Risk register for PHASE-15 itself

| Risk | Mitigation |
|------|------------|
| Doc-without-buyer (optimising for imagined enterprise) | Pause for design-partner conversation between sub-pages whenever available; revise specs based on real buyer feedback |
| Engineering atrophy during 6-10 weeks of doc work | Skip option B from PHASE-15 v2 (parallel engineering) is a deliberate choice; if DoraHacks judging arrives mid-phase, pause docs and respond |
| Solo velocity ceiling | Honest 38-50 day estimate accepts the reality; if a sub-page slips by >50% break it into smaller chunks rather than push through |
| Doc rot after PHASE-16 resumes engineering | CMP-01 mandates: every code change updates relevant doc(s) in same PR; CI runs rtm_link_check.py; pre-commit hook flags stale docs |
| 50+ doc list is wrong for actual buyers | Mitigated only by buyer conversations; PHASE-16+ may merge / split / drop docs based on what buyers actually ask for |

---

## Standing rules summary

- ops.ps1 only (waiver expired)
- backup-before-edit, no-deletion-archival
- plan-first
- read logs from runs/ directly
- 50% context warning
- docs/PHASE-N-* and docs/standards/0X/ conventions
- per-doc commit
- no shrinkage decisions without surfacing in chat first

---

**End of PHASE-15 build prompt v3 (full superset 63 docs).**
