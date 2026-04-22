# Auditex Enterprise Gap Register

Honest, ongoing catalogue of every gap between what is shipped and what a Fortune 500 CISO would sign a purchase order for. This document is authored in sprint mode, so we can correct debt as we accumulate it rather than discovering it during a customer RFP.

**Last updated:** 2026-04-22
**Current stage:** hackathon PoC (DoraHacks BUIDL #43345)
**Target stage:** enterprise-ready EU AI Act compliance platform
**Scope:** gaps only. Wins are documented in `PROJECT_STATUS.md`.

---

## How to read this document

Every gap has four fields:
- **Severity:** BLOCKER (cannot sell without fixing) / HIGH (will surface in procurement) / MEDIUM (will surface in first year of operation) / LOW (nice-to-have).
- **What shipped:** exactly what is in the codebase today.
- **What is missing:** exactly what enterprise requires that is not there.
- **Why it matters:** the specific enterprise conversation where this becomes a problem.

Estimates of effort and cost are deliberately omitted. Priority is dictated by severity, not by what is easy.

---

## Gap 1 - Signature scheme is symmetric, not third-party verifiable

**Severity:** BLOCKER

**What shipped:** HMAC-SHA256 signing in `core/reporting/export_signer.py`. A single shared secret key (EXPORT_SIGNING_KEY_HEX) is held server-side and used to both sign exports and verify them.

**What is missing:** Asymmetric signing (Ed25519 or ECDSA P-256). The private key stays with Auditex, the public key is published in a well-known location (JWKS endpoint, GitHub, domain DNS TXT record). Any third party downloads the public key and verifies the signature without trusting Auditex at all.

**Why it matters:** The entire product pitch is third-party verifiable audit. With HMAC, any party who can verify can also forge, so Auditex itself is still the only root of trust. A regulator asking for independent verification would reject HMAC. The DoraHacks submission narrative implicitly oversells this.

**Disclosed to customers as:** not yet. Must be corrected before any pilot conversation that mentions the phrase third-party verification.

---

## Gap 2 - Append-only audit trail survives INSERT/UPDATE/DELETE but not DROP/TRUNCATE

**Severity:** BLOCKER

**What shipped:** PostgreSQL trigger on the `audit_events` table that raises an exception on UPDATE and DELETE. This is enforced both in Python (repository has no update/delete methods) and at the SQL level.

**What is missing:** Real tamper-evidence. Anyone with superuser access to the database can DROP the table, TRUNCATE it, DROP the trigger first then modify rows, or restore a doctored backup. True append-only requires WORM storage (S3 Object Lock with compliance retention), a notary/timestamp service (RFC 3161), or blockchain anchoring with periodic roots committed to a public chain.

**Why it matters:** A CISO or regulator will ask: what happens if your own DBA is compromised or acts maliciously? Current answer: audit trail is lost. Correct answer must be: events are anchored externally and tampering is detectable even if Auditex itself is fully compromised.

**Disclosed to customers as:** not yet. Marketing language calls the log immutable, which is not true in the threat model regulators care about.

---

## Gap 3 - No human-in-the-loop, violating EU AI Act Article 14

**Severity:** BLOCKER

**What shipped:** A fully automated pipeline. Executor LLM + 3 reviewer LLMs + Vertex consensus. No human review step. No handoff UI. No ability to pause a task for a named human reviewer. No audit trail of who the human reviewer was.

**What is missing:** Article 14 of the EU AI Act requires effective human oversight for high-risk systems. Auditex markets itself as an EU AI Act compliance product, so an Auditex deployment that has no human oversight is itself a high-risk AI system under the Act, and therefore non-compliant with the regulation it claims to enforce. Required: a human-reviewer role, an interruptible pipeline, a review queue for flagged tasks, and audit events that record the named human reviewer and their verdict.

**Why it matters:** The product sells EU AI Act compliance but cannot sell itself to anyone using it for high-risk decisions until Article 14 is covered. Any sharp compliance officer catches this on the first 15-minute demo call.

**Disclosed to customers as:** not yet. Must be addressed in both product and pitch before Article 14 comes up in any demo.

---

## Gap 4 - Byzantine Fault Tolerance claim is architecturally real but semantically hollow

**Severity:** HIGH

**What shipped:** 3 reviewer LLMs plus a consensus evaluator. FoxMQ BFT finalises the event chain. The BFT label is technically accurate for the consensus layer.

**What is missing:** The 3 reviewers are not 3 independent trust roots. Today they are 2 GPT-4o calls plus 1 Claude call, or similar. All come from 2 commercial LLM providers, trained on similar data, served by similar infrastructure, vulnerable to similar prompt injection. If one of them has a subtle alignment failure mode, all three may share it. Classic BFT assumes independent failure modes; these failure modes are correlated.

**What is required:** (a) at least one non-LLM reviewer (rule-based, retrieval-grounded, or human), (b) an evaluation harness showing LLM verdicts match certified human auditors on a benchmark dataset, (c) documented correlation analysis across reviewer models.

**Why it matters:** The BFT framing is load-bearing for the differentiation argument. An informed technical buyer or academic reviewer will push on this within 10 minutes. The honest defence today is: the consensus mechanism is BFT, the reviewers are not independent in the information-theoretic sense.

---

## Gap 5 - Single-tenant, single API key, no workspaces

**Severity:** BLOCKER

**What shipped:** One API key per deployment. All tasks, reports, events visible to anyone with that key. No concept of organisation, workspace, tenant, or user.

**What is missing:** Org-scoped data isolation at the database layer. Per-workspace API keys. RBAC roles (Auditor, Reviewer, Admin, Compliance Officer at minimum). SSO integration (SAML 2.0 and OIDC). SCIM provisioning for user lifecycle. Per-org audit of API key usage.

**Why it matters:** No enterprise runs a multi-tenant compliance product with one shared API key. Procurement will reject at first security questionnaire. On-prem deployments partially sidestep this but still need RBAC internally.

---

## Gap 6 - No SOC 2, ISO 27001, or penetration test

**Severity:** BLOCKER

**What shipped:** Nothing. No security framework evidence. No penetration test report. No vulnerability disclosure policy. No security.txt. No SBOM.

**What is missing:** SOC 2 Type II at minimum. ISO 27001 preferred for EU customers. A published vulnerability disclosure policy, security contact, and at least one third-party penetration test. Signed SBOMs per release.

**Why it matters:** The first security questionnaire from a regulated buyer has 200 to 400 questions and assumes SOC 2 exists. No SOC 2 means no procurement conversation. SOC 2 readiness typically takes 6 to 12 months with outside auditors and dedicated controls work.

---

## Gap 7 - No data processor story under GDPR Article 28

**Severity:** BLOCKER for EU customers

**What shipped:** Auditex passes customer data to Anthropic and OpenAI APIs for executor and reviewer calls. There is no DPA, no sub-processor list, no record of processing activities, no data residency controls, no way for a customer to mark data as ineligible for third-party processors.

**What is missing:** A signed DPA template per customer naming Anthropic and OpenAI as sub-processors, a public sub-processor list, a data residency story (EU region only deployments, no cross-border transfer outside UK-EU adequacy), a mechanism to redact or locally process sensitive fields before hitting third-party LLM APIs.

**Why it matters:** An EU customer subject to GDPR cannot deploy Auditex until the data processor chain is documented. For healthcare, defence, and banking, local-model-only deployment may be required, which means supporting on-prem open-source models as reviewer options.

---

## Gap 8 - Article 9, 13, 17 mapping is a technical guess, not legally reviewed

**Severity:** HIGH

**What shipped:** Hard-coded article mapping in the report generator. Article 9 mapped to risk assessment plus confidence score. Article 13 mapped to reasoning chain plus consensus. Article 17 mapped to commitment-verified review process plus DLQ.

**What is missing:** A barrister or EU-qualified AI law specialist sign-off that these mappings are defensible under the final text of the Act and its implementing guidance. The Article 17 mapping is the weakest, a commitment-verified review process is a creative reading that may not survive scrutiny. Missing articles that may actually apply: 10 (data and data governance), 11 (technical documentation), 12 (record-keeping), 15 (accuracy, robustness, cybersecurity).

**Why it matters:** If a regulator rejects the mapping during an audit, the whole value proposition collapses. A legal review turns a hand-wavy claim into a defensible product claim.

---

## Gap 9 - No observability, SLO story, or incident process

**Severity:** HIGH

**What shipped:** Celery logs, application logs written to runs/. Nothing else. No Prometheus metrics, no Grafana dashboards, no Sentry error tracking, no uptime monitor, no published SLO, no runbook, no on-call.

**What is missing:** Structured metrics (per-endpoint latency, per-LLM-provider latency and error rate, queue depth, per-task duration, per-tenant usage), error tracking, an SLO for availability and for end-to-end task completion time, a status page, a published incident communications template, an on-call rotation (even if it is a single founder).

**Why it matters:** Every enterprise RFP asks for SLO commitments. No metrics means no SLO, and no SLO means a capped contract value and penalty-free termination clauses.

---

## Gap 10 - No load testing, no disaster recovery, single-AZ

**Severity:** HIGH

**What shipped:** Docker Compose single-host deployment. Local PostgreSQL. Local Redis. Local FoxMQ. No backups tested. No RPO/RTO documented.

**What is missing:** A multi-AZ or at least documented failure story. Backups tested with a restore drill. RPO and RTO committed in writing. A load test showing behaviour at 10x, 100x, 1000x current throughput. Chaos test showing behaviour when Anthropic or OpenAI is degraded.

**Why it matters:** Procurement asks for RPO and RTO in questionnaires. If the answer is we have not tested backups, the conversation ends.

---

## Gap 11 - Cost model does not scale

**Severity:** HIGH

**What shipped:** Every task makes 4 LLM calls (1 executor plus 3 reviewers) plus 1 more for the compliance narrative. Roughly 5 calls per audit.

**What is missing:** A tiered consensus strategy. Low-stakes tasks should use fewer reviewers. Borderline confidence scores should escalate to more reviewers or human. Cost per audit needs to be observable per-tenant. A customer doing thousands of audits per day today would generate $300 to $15K per day in LLM costs, which makes per-seat SaaS pricing infeasible and per-audit pricing awkward.

**Why it matters:** Either the customer burns their own LLM budget at a rate they cannot sustain, or Auditex eats it, or the pricing model is built around the cost which forces a narrower market.

---

## Gap 12 - Frontend is a developer dashboard, not a compliance-officer product

**Severity:** MEDIUM

**What shipped:** A task submission form, a task list, a task detail page with expandable pipeline steps, a sign and verify panel, an EU AI Act accordion, a JSON export download.

**What is missing:** Bulk operations (import a CSV of 10,000 tasks, run them overnight). Saved searches and filters (show me all REJECT decisions in Q3 2026 above confidence 0.8). Templates (create a contract-check preset reused by the whole team). Scheduled reports delivered by email. An approvals workflow for human reviewers. An admin panel. A customer-facing API-key rotation UI. A usage billing dashboard. A customisable compliance report format matching the customers internal audit template.

**Why it matters:** A compliance officer looking at the current UI sees a developer tool, not a workflow product. The evaluation moves from is this product-market-fit to when you have built the product let us talk again.

---

## Gap 13 - LLM output is not validated against a benchmark of certified auditors

**Severity:** HIGH

**What shipped:** The executor plus reviewers produce APPROVE / REJECT / REQUEST_AMENDMENTS / REQUEST_ADDITIONAL_INFO verdicts. Playwright tests assert shape not correctness. Nobody has measured whether the verdicts agree with a real compliance professional on a real corpus.

**What is missing:** An evaluation dataset of at least 200 documents across document_review, risk_analysis, contract_check, each labelled by a certified human auditor. A regression harness that runs Auditex on that set and reports precision, recall, agreement rate. A public benchmark number (we agree with certified auditors 87 percent of the time) that gives buyers a concrete quality signal.

**Why it matters:** Without this number the pitch is trust our pipeline. With it the pitch becomes here is the measured agreement with humans, and here is where we under-perform. The second pitch closes deals. The first does not.

---

## Gap 14 - No vendor lock-in protection for the customer

**Severity:** MEDIUM

**What shipped:** Exports are in JSON with a schema. Audit events are in PostgreSQL. No export-everything, no signed data-portability archive, no documented migration path.

**What is missing:** A one-click export-everything button that produces a signed tarball of every event, report, and signature for the tenant. Documented schemas covered by a compatibility promise. A tool to replay events from the tarball into a fresh Auditex instance. A public commitment to data portability.

**Why it matters:** Large customers will ask what happens if you go bankrupt or get acquired. Data portability is table stakes for regulated vertical SaaS.

---

## Gap 15 - No defensive patent filing and no open-source licence strategy

**Severity:** MEDIUM

**What shipped:** The repository has no LICENSE file. The multi-agent BFT consensus audit pattern, the /events/{task_id}/verify endpoint, and the signed bundle format are all novel and unprotected.

**What is missing:** A LICENSE file. A licence choice that matches the go-to-market (Apache 2.0 for broadest adoption, BSL/SSPL if commercial gating is desired, proprietary if closed-source is desired). A defensive patent filing or a public prior-art post covering the novel architecture patterns so they cannot be patented against the project later.

**Why it matters:** Big AI players filing in this space could block future commercialisation. A clear licence removes ambiguity for design partners and contributors.

---

## Gap 16 - Marketing and submission narrative are enterprise-confident, product is PoC

**Severity:** HIGH

**What shipped:** DoraHacks BUIDL #43345 describes Auditex in enterprise-confident language (third-party-verifiable, BFT consensus, immutable, EU AI Act coverage) that exceeds what the code actually delivers today. Gaps 1, 2, 3, 4, 8 in this register are implicit over-claims in that narrative.

**What is missing:** Honesty calibration. A revised submission body that separates the thesis from the current implementation. A clear roadmap section that lists what the PoC does not yet do. A short disclosures section.

**Why it matters:** If a judge, journalist, or design partner discovers the gap between narrative and reality before the project discloses it, credibility collapses. If the project discloses it first and pairs it with a credible plan, credibility compounds.

---

## Summary table

| # | Gap | Severity | Disclosed? |
|---|-----|----------|------------|
| 1 | HMAC signing not third-party verifiable | BLOCKER | No |
| 2 | Audit trail vulnerable to DROP/TRUNCATE | BLOCKER | No |
| 3 | No human-in-the-loop (Article 14) | BLOCKER | No |
| 4 | BFT reviewers have correlated failure modes | HIGH | No |
| 5 | Single-tenant, no SSO, no RBAC | BLOCKER | No |
| 6 | No SOC 2 / ISO 27001 / pen test | BLOCKER | No |
| 7 | No DPA / sub-processor story (GDPR 28) | BLOCKER (EU) | No |
| 8 | Article mapping not legally reviewed | HIGH | No |
| 9 | No metrics, SLO, or on-call | HIGH | No |
| 10 | No load test, no DR, single-AZ | HIGH | No |
| 11 | 5 LLM calls per audit does not scale | HIGH | No |
| 12 | UI is developer tool, not compliance product | MEDIUM | No |
| 13 | No benchmark against certified auditors | HIGH | No |
| 14 | No data portability / export-everything | MEDIUM | No |
| 15 | No licence file, no defensive patent | MEDIUM | No |
| 16 | Submission narrative over-claims | HIGH | No |

**Count:** 6 BLOCKERs, 7 HIGH, 3 MEDIUM, 0 LOW.

---

## Reading guide for the uncomfortable parts

Six BLOCKER gaps is normal for a hackathon PoC aimed at enterprise. It is not a verdict that the project is doomed. It is a map.

The submission already delivers: a novel thesis (multi-agent BFT consensus as Article 13 primitive), a working end-to-end implementation at 100% test coverage, and a third-party verify endpoint that no competitor offers. The thesis is defensible. The gaps are execution, not architecture.

Two gaps (1 and 16) are honesty debts that should be paid before any customer conversation, because they change how we describe the product, not what the product does. These are cheap.

Two gaps (3 and 5) are product-shape gaps that change the architecture. Human-in-the-loop is not just an extra screen, it is a new role, a new event type, a new queue state, and a new audit-event schema. Multi-tenancy is not a middleware switch, it is a database-level redesign.

Two gaps (6 and 7) are process gaps that cannot be engineered around. SOC 2 and DPA have to be done by humans with legal hats. Money and calendar time, not code.

Everything else is incremental. None of it kills the project. All of it is required.

---

## What this document is for

1. A source of truth when a judge, design partner, or investor asks what is the current state of the product.
2. A checklist to work against, phase by phase, as the product matures.
3. A commitment that future work will continue to document debt as it is taken, not discover it in a procurement call.
4. An honesty signal. Enterprise buyers trust vendors who know what they do not yet have.

Updates to this register are part of the definition-of-done for every future commit that touches a relevant subsystem. If a commit fixes a gap, it is marked fixed here in the same PR. If a commit introduces a new gap, it is added here in the same PR.
