# Phase 7 Changes — Audit Record
# Auditex Dashboard Frontend
# Date: 06/04/2026
# Status: MT-008 PASSED 5/5

---

## Files Created (new in Phase 7)

### Frontend scaffold
- frontend/package.json          — React 18, Zustand, Vite, Tailwind, Playwright
- frontend/tsconfig.json         — TypeScript config with vite/client types
- frontend/tsconfig.node.json    — Node tsconfig for Vite
- frontend/vite.config.ts        — Vite dev server, proxy /api -> :8000
- frontend/tailwind.config.js    — Tailwind content paths
- frontend/postcss.config.js     — PostCSS with Tailwind + autoprefixer
- frontend/index.html            — Vite entry, title: Auditex — AI Compliance Dashboard
- frontend/Dockerfile            — Multi-stage: node:20-alpine build + serve
- frontend/playwright.config.ts  — Playwright E2E config, headed, chromium

### App source
- frontend/src/index.css         — Tailwind base/components/utilities
- frontend/src/main.tsx          — React 18 createRoot entry
- frontend/src/vite-env.d.ts     — /// <reference types="vite/client" /> for import.meta.env
- frontend/src/App.tsx           — Root component, 3-panel layout, polling lifecycle
- frontend/src/types/index.ts    — TypeScript types matching API response shapes
- frontend/src/services/api.ts   — Typed fetch wrapper, all API calls
- frontend/src/store/taskStore.ts — Zustand store, polling, task state
- frontend/src/components/StatusBadge.tsx    — Reusable status badge with pulse animation
- frontend/src/components/SubmitTaskForm.tsx — Task submission form
- frontend/src/components/TaskList.tsx       — Scrollable task list, newest first
- frontend/src/components/TaskDetail.tsx     — Full task detail, lifecycle, report, export

### Tests
- frontend/tests/dashboard.spec.ts  — Playwright E2E: TC-01, TC-02, TC-03
- frontend/tests/tsconfig.json      — ESM-aware tsconfig for Playwright runner

### Backend additions
- backend/scripts/verify_task_data.py — DB verification script, shows last 5 tasks

### Documentation
- docs/testing/manual-test-scripts/MT-008-dashboard.ps1 — Manual test script
- docs/PHASE-7-CHANGES.md (this file)

---

## Files Modified (pre-existing, changed in Phase 7)

### docker-compose.yml
- Added frontend service: node:20-alpine, port 3000, VITE_API_KEY, VITE_API_URL, depends_on api

### backend/app/api/v1/tasks.py
- POST /api/v1/tasks response: added task_type and report_available fields
- GET  /api/v1/tasks list response: added report_available to every task row
- Reason: frontend crashed (white screen) when report_available was undefined

---

## Bug Fixes Applied During Phase 7

### Bug 1 — npm ci failed in Docker (fix: npm install)
- Dockerfile used `npm ci` which requires package-lock.json
- Fix: changed to `npm install`, removed package-lock.json from COPY

### Bug 2 — TypeScript errors in Docker build
- TS6133: `currentOrder` declared but never read in TaskDetail.tsx
- TS2339: `import.meta.env` not recognised (missing vite/client types)
- Fix: removed unused var, added vite-env.d.ts + tsconfig types entry

### Bug 3 — Polling stopped immediately on page load
- Store auto-stopped polling when all existing tasks were settled
- New tasks submitted would not appear or update
- Fix: polling runs continuously while App is mounted, never auto-stops

### Bug 4 — White screen on submit (critical)
- API POST /tasks response missing report_available field
- API GET  /tasks list response missing report_available field
- Frontend types used wrong field names: executor_output/review_results/vertex_proof
  (API actually returns: executor/review/vertex)
- Frontend submitTask sent flat body; API expects { task_type, payload: { document, ... } }
- Frontend listTasks sent ?size=50; API param is ?page_size=50
- Fix: corrected all field names, added normalise() guard in store, fixed API request shapes

### Bug 5 — Playwright TC-02 badge selector never matched
- Selector looked for terminal status badge only
- Task was still EXECUTING/REVIEWING during the 57s test window
- Fix: log ALL span texts each poll cycle, timeout extended to 180s

---

## Files Never Modified

- run.ps1          — original Phase 0 script, untouched
- commit.ps1       — original Phase 0 script, untouched
- Makefile         — original Phase 0, untouched
- All Phase 1-6 backend files — untouched except tasks.py (documented above)

---

## MT-008 Result

PASSED 5/5 — 06/04/2026 01:34:50
  ✓ Dashboard loads without errors
  ✓ Task appears in list at QUEUED after submit
  ✓ Status updates in real time (3s polling)
  ✓ View Report shows PoC report content
  ✓ Export EU AI Act JSON downloads file

---

## Git Reference

Phase 6 commit: bed38f1
Phase 7 commit: (pending — run git add -A && git commit)
