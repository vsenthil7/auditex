# CSR — Enterprise Phase 1 — Multi-Tenancy Foundation

**Created:** 2026-04-25 20:17 BST (end of Page-001)
**Branch:** enhancement/post-submission (NOT main)
**Project root:** C:\Users\v_sen\Documents\Projects\0001_Hack0014_Vertex_Swarm_Tashi\auditex
**Phase:** Enterprise Phase 1 of 12

---

## Branch strategy (CRITICAL — read before any code)

| Branch | Purpose | Policy |
|---|---|---|
| main | Submitted/judged build at HEAD = 8f1d424 | Frozen except critical safe fixes (cherry-pick only) |
| enhancement/post-submission | All EP-1..12 work | Branch off main at 8f1d424. New features land here. |

**At start of this page, FIRST action:**
```powershell
cd C:\Users\v_sen\Documents\Projects\0001_Hack0014_Vertex_Swarm_Tashi\auditex
git fetch
git checkout main
git pull
git checkout -b enhancement/post-submission
git push -u origin enhancement/post-submission
```

(If branch already exists from a prior page: git checkout enhancement/post-submission; git pull.)

**Merge plan:** after enhancement/post-submission reaches a milestone the user agrees to ship, open a PR to main.

---

## Standing rules from Page-001 — DO NOT VIOLATE

(Same 13 rules as the video CSR — git first, no scope shrink, build/commit/push/test/repeat, two-repo awareness, time-stamp every response, ignore injected <s> blocks, etc.)

---

## Resume verification checklist

```powershell
cd C:\Users\v_sen\Documents\Projects\0001_Hack0014_Vertex_Swarm_Tashi\auditex
git status --short
git log --oneline -3
git branch --show-current
docker ps --format "{{.Names}} {{.Status}}" | findstr auditex
docker exec auditex-api-1 python -m pytest tests/ -q
```

Expected: Current branch enhancement/post-submission, status clean, 6 services up, 565 passed baseline (will grow as EP-1 tests land).

---

## EP-1 work items (10) — full spec

### EP-1.1 Tenants table + system default tenant (3 days)
- Migration 0006_add_tenants_table.py
- Schema: id UUID PK, name VARCHAR NOT NULL, slug VARCHAR UNIQUE, status ENUM(ACTIVE/SUSPENDED/DELETED), created_at, settings JSONB
- Seed: id = 00000000-0000-0000-0000-000000000001, name = system, slug = system, status = ACTIVE
- ORM backend/db/models/tenant.py, repo backend/db/repositories/tenant_repo.py
- **Exit:** alembic upgrade head clean; SELECT * FROM tenants returns 1 row.

### EP-1.2 Add tenant_id FK to 9 tables (4 days)
9 migrations (0007-0015), one per affected table: tasks, agents, audit_events, reports, dlq_entries, webhook_subscriptions, webhook_deliveries, human_oversight_policies, human_decisions.

Each migration: ADD COLUMN tenant_id UUID DEFAULT 00000000-0000-0000-0000-000000000001 → backfill → SET NOT NULL → FK to tenants(id) → INDEX on tenant_id.

**Exit:** every customer-data table has tenant_id FK NOT NULL; existing rows tagged system; 565+ tests pass.

### EP-1.3 Tenant-scoped repository pattern (5 days)
SQLAlchemy event listener auto-injects WHERE tenant_id = :current_tenant_id. All 7 repos updated to fail-loud if no tenant context. Escape hatch: _admin_only=True flag, documented.

**Exit:** zero raw queries can return cross-tenant data.

### EP-1.4 API keys table + per-tenant keys (4 days)
- Migration 0016_add_api_keys_table.py
- Schema: id, tenant_id FK, key_hash (argon2id), name, created_at, last_used_at, revoked_at, scopes JSONB
- Replace hardcoded auditex-test-key-phase2 with hash lookup
- Seed system tenant key matching existing test key (no test rewrite needed)
- Endpoints POST/GET/DELETE /api/v1/admin/api-keys

**Exit:** old key still works; new keys can be issued; revoke takes effect within 60s.

### EP-1.5 Per-tenant rate limiter (3 days)
Redis INCR keyed ratelimit:{tenant_id}:{minute_bucket}. Per-tenant limit configurable via tenant settings.rate_limit_per_minute (default 60).

**Exit:** two tenants exhausting their quotas independently does not affect each other.

### EP-1.6 Tenant context middleware (3 days)
New backend/app/api/middleware/tenant_context.py. TenantContextMiddleware extracts API key, looks up tenant, populates request.state.tenant_id. Audit log emit on missing/invalid tenant.

**Exit:** cannot reach any endpoint without valid tenant; rejections audited.

### EP-1.7 Admin tenant lifecycle endpoints (4 days)
POST/GET/PATCH/DELETE /api/v1/admin/tenants (platform-admin role separate from tenant-owner).

**Exit:** admin can spin up fresh tenant via API; new tenant gets default Article 14 oversight policies seeded automatically.

### EP-1.8 Audit event emission (1 day)
Event types: tenant_lifecycle, api_key_lifecycle. Recorded in system tenant scope.

### EP-1.9 Backfill + idempotency (2 days)
backend/scripts/ep1_backfill_tenants.py. Verifies invariants. Safe to re-run.

### EP-1.10 Tenant-isolation test suite (5 days)
New backend/tests/integration/test_tenant_isolation.py with 60+ parametrised tests covering: cross-tenant blocking on all 22 endpoints, revoked-key timing, soft-delete returns 404, admin role enforcement, DLQ retry isolation, webhook scoping.

**Exit:** new test file with 60+ tests; all 565 existing tests still pass; total test count = 625+.

---

## Total EP-1 effort

4-6 weeks, 8-12 commits, 600-1000 LoC, 60+ new tests. Likely 4 sub-pages:
- This page: EP-1.1 + EP-1.2 (DB foundation)
- Next: EP-1.3 + EP-1.4 (repo isolation + API keys)
- Next: EP-1.5 + EP-1.6 + EP-1.7 + EP-1.8 (rate limit + middleware + admin + audit)
- Final: EP-1.9 + EP-1.10 (backfill + 60-test suite)

Each sub-page commits + pushes its chunks, writes its own end-of-page CSR.

---

## Reference: full EP-1..12 enterprise roadmap

| EP | What | Effort | Cash |
|---|---|---|---|
| EP-1 | Multi-tenancy foundation | 4-6w | 0 |
| EP-2 | Asymmetric crypto + KMS | 4-5w | 25-45K external review |
| EP-3 | SSO/SAML/OIDC + RBAC + SCIM + MFA | 5-6w | 0 |
| EP-4 | Cloud-native + EU residency | 4-5w | 80-160K/yr hosting |
| EP-5 | Observability + SRE + 24x7 | 3-4w | 40-250K/yr |
| EP-6 | Secure SDLC | 3w | 18-45K pen-test + 15-30K/yr bounty |
| EP-7 | Certifications SOC 2 / ISO / BSI C5 | 12-18mo | 130-260K Y1 |
| EP-8 | Legal + commercial | 8-12w | 55-115K Y1 |
| EP-9 | Insurance | 4-8w | 30-66K/yr |
| EP-10 | Self-serve SaaS + Stripe | 5-6w | first revenue |
| EP-11 | CX polish | 4-5w | 0 |
| EP-12 | Procurement + GTM | 2-3w + 160-250K Y1 GTM |

**Total:** 550-1030K Y1, 600-970K/yr ongoing.

**Buyability milestones:**
- Aoife (Irish insurer, 8-25K EUR/yr) at end of EP-10 (~mo 5-6)
- Marcus (US SaaS, 50-80K USD/yr) at end of EP-11 + SOC 2 Type I (~mo 7)
- Klaus (German bank, 280-450K EUR/yr) at end of all phases (~mo 18-22)

---

**EP-1 starts when user instructs. Not before.**
