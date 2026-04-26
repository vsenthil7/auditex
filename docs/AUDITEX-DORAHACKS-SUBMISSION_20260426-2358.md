# Auditex - EU AI Act Compliance Audit Pipeline

**TL;DR:** A multi-agent audit trail platform that produces cryptographically-verifiable compliance reports for AI-assisted decisions, with full Article 14 human oversight, directly mapped to EU AI Act Articles 9, 13, 14, and 17.

---

## The Problem

The EU AI Act carries fines up to 7% of global annual revenue for non-compliance with high-risk AI obligations. Yet most AI systems in production today are black boxes:

- No auditable record of which model made a decision
- No verifiable proof that a reviewer actually reviewed
- No tamper-evident trail that would survive a regulator audit
- No human-in-the-loop control as required by Article 14
- No standard way to map AI outputs to specific EU AI Act articles

Auditex turns every AI decision into a signed, third-party-verifiable audit artifact - with configurable human override at every step.

---

## How It Works

Auditex runs every decision through a 5-stage pipeline with cryptographic proof at each step, plus an optional human gate for Article 14 compliance:

1. **Submission** - Task enters the queue (FoxMQ/Redis) with a criteria spec.
2. **AI Executor** - Claude Sonnet produces a primary recommendation + reasoning + confidence score.
3. **Review Panel** - Three independent reviewer LLMs (GPT-4o x 2 + Claude) produce verdicts with commitment hashes. Byzantine Fault Tolerant consensus requires at least 2-of-3 agreement.
4. **Human Oversight (Article 14)** - If the per-task-type policy requires human review, the task pauses at AWAITING_HUMAN_REVIEW. A named human reviewer makes a decision (APPROVE / REJECT / REQUEST_AMENDMENTS) via a queue UI. Decisions are immutable per-reviewer rows tied into the audit chain. N-of-M quorum supported per task type.
5. **Vertex Consensus** - FoxMQ BFT finalises the event chain with an immutable vertex_event_hash and round number. Human signatures included in payload when present.
6. **Compliance Report** - LLM-generated plain-English summary + structured EU AI Act Article 9 / 13 / 17 JSON export, cryptographically signed (HMAC-SHA256).

Every artifact is independently verifiable: download the signed bundle, recompute the hash chain via `GET /events/{task_id}/verify`, compare against the stored Vertex proof. No server trust required.

---

## EU AI Act Coverage

| Article | What Auditex Provides |
|---------|----------------------|
| Article 9 - Risk Management | Risk assessment label + confidence score per decision, retained in append-only audit events |
| Article 13 - Transparency | Full reasoning chain (executor + 3 reviewers) + consensus outcome + human-readable summary |
| Article 14 - Human Oversight | Configurable N-of-M human decision quorum per task type, immutable per-reviewer audit rows tied into Vertex chain, admin UI for policy configuration, queue UI for reviewers, REJECT-overrides-all + REQUEST_AMENDMENTS-overrides-APPROVE rule, optional auto-commit on timeout |
| Article 17 - Quality Management | Commitment-verified review process, DLQ-backed retry with tamper-evident sequence |

---

## Architecture

- **Backend:** FastAPI + Celery + PostgreSQL + Redis, 100% pytest coverage (565 tests)
- **Consensus:** FoxMQ BFT (LIVE) with deterministic stub fallback for dev/test
- **Human oversight:** alembic 0005 schema (human_decisions + human_oversight_policies), pure-function policy logic with 100% line coverage, Celery finalise-after-human-quorum task
- **Reporting:** LLM-generated compliance narratives with HMAC-SHA256 export signing
- **Frontend:** React + TypeScript + Zustand + Playwright (109 vitest tests at 100% coverage), 3-tab UI (Dashboard / Human Review / Oversight Config)
- **Cryptography:** SHA-256 chain hash, commitment-reveal reviewer pattern, HMAC signatures, schema_version 1.1 with human_decisions_hash for tamper-evidence
- **Audit trail:** PostgreSQL trigger-enforced append-only audit_events table - no UPDATE, no DELETE, ever

---

## Novel Contributions

1. **Multi-agent consensus as compliance primitive** - not just for LLM answer quality, but as the literal Article 13 transparency mechanism.
2. **Article 14 as first-class workflow gate** - not bolted on. Configurable per-task-type policy. Human signatures cryptographically tied into the same Vertex chain as the AI verdicts.
3. **Third-party verification endpoint** - `/events/{task_id}/verify` re-hashes the chain server-side, so even Auditex itself cannot retroactively lie about what happened.
4. **EU AI Act as data model** - Article numbers are first-class schema keys, not afterthought tags.
5. **Signed bundle download** - every report ships with its HMAC signature and key ID, so auditors can validate offline.

---

## Tech Stack

FastAPI, Celery, PostgreSQL, Redis, FoxMQ BFT, Claude Sonnet, GPT-4o, React, TypeScript, Zustand, Vite, Playwright, Vitest, pytest, Docker Compose, jsonschema, HMAC-SHA256, alembic.

---

## Current State - 85% Built, 15% Funded External Work

Auditex is a validated proof-of-concept with novel architecture. The honest gap catalogue is committed to the repository as `docs/ENTERPRISE-GAP-REGISTER.md`: 16 gaps identified at the start of the project, 1 RESOLVED (Article 14 shipped 25 April 2026), 5 BLOCKER, 7 HIGH, 3 MEDIUM remaining.

### What is shipped and works (the 85% I built solo)

- 4-LLM BFT consensus pipeline (executor + 3 reviewers + Vertex finalisation)
- **Article 14 human oversight** end-to-end: 16 unit tests on the policy module, 11 integration tests on the 4 API endpoints + worker gate, 3 Playwright E2E covering full submit -> AWAITING -> APPROVE -> COMPLETED flow
- 565 backend pytest at 100% line coverage + 109 frontend vitest at 100% coverage
- Append-only PostgreSQL audit events with trigger-level enforcement
- HMAC-SHA256 signed exports + third-party verify endpoint
- Plain-English compliance narratives + EU AI Act Article 9 / 13 / 17 JSON export
- Docker-Compose reproducible end-to-end deployment
- 6-scenario captioned demo video (3 task types x 2 paths each: auto vs human-in-loop with APPROVE / REJECT / REQUEST_AMENDMENTS), shipped on DoraHacks BUIDL #43345

### What I can develop solo, but is pending the next sprint (still in the 85%)

These are technical items I can implement myself with the existing skill set, but were not in the hackathon scope:

- Frontend polish: better task-detail visualisation, downloadable audit bundle UX
- Performance: query indexing for queue endpoints, caching layer for repeated report fetches
- Observability: Prometheus metrics endpoint, structured request logging with request_id correlation
- DR + ops: backup/restore runbook, postgres replication setup, basic SLO definitions
- Integration tests: extended Playwright coverage of edge cases (timeout auto-commit, REJECT-overrides-all, mismatched policy)
- Multi-provider model adapters: Gemini and on-prem open-source models as reviewer options (architecture is already pluggable, just needs adapter implementations)

### What needs external help (the 15% requiring funding)

These require legal review, certified audits, or specialist external firms - not solo engineering work:

1. **Asymmetric signing rewrite** - Ed25519 / ECDSA P-256 to replace HMAC, so verification is genuinely trustless. Requires cryptography review by an external specialist before going to production.
2. **Legal review of Article mappings** - the Article 9 / 13 / 14 / 17 mapping is engineer-authored. A barrister specialising in EU AI Act regulation must review and sign off the schema before any pilot conversation.
3. **WORM storage / notary anchoring** - postgres trigger only. Survives INSERT/UPDATE/DELETE but not DROP/TRUNCATE/malicious backup restore. Requires S3 Object Lock with compliance retention or RFC 3161 timestamp service or blockchain anchoring.
4. **Multi-tenancy + RBAC + SSO** - SAML 2.0 + OIDC + SCIM. Implementable solo, but requires SOC-2-aligned identity provider integration patterns I do not have audit experience with.
5. **SOC 2 Type II + ISO 27001 + penetration test** - external auditors and 6-12 months of observed controls. Cannot be done solo.
6. **GDPR Article 28 DPA** - signed DPA template per customer, public sub-processor list (Anthropic + OpenAI named), data residency story for EU-region-only deployments. Requires data protection officer involvement.
7. **LLM-vs-human-auditor benchmark** - paid certified human auditors validating LLM verdicts on a benchmark dataset. Not solo work; needs the human auditors and a published methodology paper.
8. **Compliance/sales co-founder** - SOC 2 readiness, design partner conversations, pilot procurement cannot run in parallel with solo product engineering.

---

## Funding Plan by Time Horizon

| Horizon | Funding Ask | Use of Funds | Exit Criterion |
|---------|-------------|--------------|----------------|
| 3 months | GBP 50K (seed-stage pre-commit) | Ed25519 signing rewrite, basic multi-tenancy, 2 LLM benchmark runs vs human auditors, incorporation + legal review of Article mapping (barrister), 20 design-partner conversations | At least 3 signed NDA pilots |
| 6 months | GBP 250K (pre-seed) | First full-time hire (compliance/sales co-founder), SOC 2 readiness consultation, WORM storage integration, Article 14 reviewer-handoff polish, first paid pilot at GBP 25K ARR | GBP 50K+ ARR, SOC 2 Type I audit scheduled |
| 12 months | GBP 1M (seed round) | 2 additional engineers (security + frontend), SOC 2 Type II certification completed, multi-provider model adapters (Claude + GPT + Gemini + open-source on-prem), notary/blockchain anchoring, enterprise procurement-ready documentation | GBP 250K ARR, 5 paying customers, 1 enterprise logo |
| 24 months | GBP 3-5M (Series A) | Team of 8-12, ISO 27001 certification, on-prem appliance for regulated industries (banking, defence, healthcare), vertical compliance packs (FCA, HIPAA, SOX extensions), EU-qualified AI auditor partnership | GBP 2M+ ARR, 20+ enterprise customers, breakeven path visible |

### Why each tranche is needed

- **3 months / GBP 50K:** Without asymmetric signing the third-party-verification pitch is technically false. Without legal sign-off on Article mappings a single regulator conversation collapses the value prop. These two alone consume the tranche. Design-partner conversations happen in parallel and decide whether Phase 2 continues at all.
- **6 months / GBP 250K:** Procurement teams require SOC 2 evidence before even running a pilot. A solo founder cannot run SOC 2 + sales + product simultaneously - a compliance/sales co-founder is the unlock.
- **12 months / GBP 1M:** SOC 2 Type II takes 6-12 months of observed controls. Enterprise customers will not sign annual contracts without it. Additional engineers allow parallel work on observability, multi-provider adapters, and notary anchoring.
- **24 months / GBP 3-5M:** Once SOC 2 exists, go-to-market shifts from design-partner hustle to regulated-vertical expansion. Each vertical (banking, defence, healthcare) requires its own compliance pack and sales motion.

### Target Metrics by Horizon

|              | ARR        | Customers           | Team   | Key Capability                  |
|--------------|------------|--------------------|--------|---------------------------------|
| 3 months     | GBP 0      | 3 pilots (unpaid)  | 1      | Ed25519 + legal mapping         |
| 6 months     | GBP 50K    | 2 paid             | 2      | SOC 2 Type I in progress        |
| 12 months    | GBP 250K   | 5 paid + 1 enterprise | 4    | SOC 2 Type II live              |
| 24 months    | GBP 2M+    | 20+ paying         | 8-12   | ISO 27001 + on-prem appliance   |

---

## SWOT Analysis

### Strengths
- Novel architectural thesis: multi-agent BFT consensus as Article 13 transparency primitive. No competitor approaches EU AI Act compliance this way.
- **Article 14 already shipped** - human oversight is not a roadmap item, it is in the demo.
- Third-party verify endpoint: cryptographic audit that does not require trusting the vendor. Unique in the market.
- EU AI Act as first-class schema: Article numbers are top-level JSON keys, not tags. Defensible as purpose-built, not repurposed.
- Engineering discipline: 100% test coverage at hackathon pace is uncommon. Architecture quality signals a team that can ship reliably.
- Timing: EU AI Act enforcement window is the 2026-2028 buying cycle.

### Weaknesses
- Moat erosion risk: Anthropic or OpenAI shipping native audit mode collapses differentiation. 12-24 months likely.
- Solo-founder velocity ceiling: current pace does not scale to SOC 2 + sales + support simultaneously.
- LLM cost at scale: 5 API calls per audit breaks per-seat pricing; per-audit pricing is awkward.
- No regulatory track record: no Auditex-produced report has yet survived a regulator audit. Claim is untested.
- Reviewer correlation: 3 LLMs from 2 providers is not 3 independent trust roots.

### Opportunities
- Multi-provider neutrality: Anthropic cannot credibly sell audit trail that works across competitors. Auditex can.
- On-prem / air-gapped regulated industries: banking, defence, healthcare cannot use cloud-only AI audit services. Natural moat for self-hostable deployments.
- Compliance pack verticals: UK FCA, US HIPAA, US SOX each deserve a purpose-built Article-equivalent mapping. Land-and-expand motion.
- Open-source distribution: BSL or Apache-licensed core with commercial extensions could seed rapid adoption before incumbents notice.
- Defensive patent: the multi-agent BFT audit pattern (with Article 14 human gate) is genuinely novel and filable.

### Threats
- Anthropic / OpenAI native audit mode released with bundled pricing and trusted signing. Highest-likelihood threat, 12-24 month horizon.
- Incumbent ML governance vendors (Credo AI, Holistic AI, Fiddler, Arize) pivot into cryptographic audit as a feature. 6-18 months possible.
- EU AI Act enforcement delay or softening: reduces urgency, lengthens buying cycles, shrinks market timing.
- LLM API price increase: could double cost-per-audit overnight, killing the unit economics.
- Regulator rejection of LLM-based reviewers: less of a threat now Article 14 human override is shipped, but if any EU regulator explicitly states LLM verdicts are not acceptable as primary evidence, the value prop weakens.
- Commoditisation of EU AI Act compliance: major consultancies (Deloitte, EY, PwC) ship white-labelled audit tooling bundled with advisory.

### Strategic Response
- **Against Anthropic / OpenAI:** emphasise multi-provider neutrality and on-prem. Do NOT try to out-build them on cloud.
- **Against incumbents:** move faster on SOC 2 and first customer logos before they pivot.
- **Against regulatory uncertainty:** Article 14 human-in-the-loop already shipped, so the regulator-rejects-LLM-verdicts scenario does not collapse the product.
- **Against consultancy white-labels:** position as the underlying tooling that consultancies resell, not the consultancy itself. Partnership motion, not competitive motion.

---

## Links

- **Demo video (DoraHacks BUIDL #43345):** https://youtu.be/ydcLTZsgxuk
- **GitHub:** https://github.com/vsenthil7/auditex
- **Gap register:** https://github.com/vsenthil7/auditex/blob/main/docs/ENTERPRISE-GAP-REGISTER.md

All code, tests, coverage reports, and EU AI Act export schemas are open for inspection.
