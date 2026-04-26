# PHASE-15 Build Prompt

**Phase:** PHASE-15 - Post-Submission Cleanup + EP-1 Kickoff
**Trigger:** PHASE-14 video submission complete (DoraHacks BUIDL #43345 + YouTube unlisted live)
**HEAD at start:** 19ae177 (or whatever HEAD reaches by PHASE-15 start)
**Next session:** Read this file first.

## Goal

Two parallel tracks:

**Track A - Cleanup carry-forward** (~30 min, do early)
Clean up the misplaced files and tech debt accumulated in PHASE-13 and PHASE-14.

**Track B - Post-submission monitoring** (passive, runs throughout)
Monitor DoraHacks for judging response. React based on outcome.

**Track C - EP-1 multi-tenancy** (the real next big thing)
Start EP-1 multi-tenancy work on the `enhancement/post-submission` branch.
Multi-tenancy is BLOCKER #5 in the gap register and is the prerequisite for any
commercial pilot conversation.

## Track A - Cleanup carry-forward

### A.1 Misplaced pages/ folder

`pages/` directory currently contains 3 subdirs that should not be there. The
auditex convention is `docs/PHASE-N-*` for handoff docs, not `pages/*/session_prompt.md`.

**Read before delete** (do not lose content):
- `pages/Page-002-Video-Refresh/session_prompt.md` - this was the PHASE-14 work plan,
  now superseded by `docs/PHASE-14-BUILD-PROMPT.md`. Safe to delete after confirming
  no unique content.
- `pages/PageN-EP1-Multi-Tenancy/session_prompt.md` - this is the EP-1 spec content
  that needs RELOCATION to `docs/PHASE-N-EP1-MULTI-TENANCY-PROMPT.md` before
  the source is deleted.
- `pages/Page-002-EP1-Multi-Tenancy/` - third subdir found in PHASE-14 listing.
  Inspect contents before delete.

### A.2 Other cleanup items

- `scripts/write_csr_page002.py` - delete (CSR was invented jargon, not used)
- `Project-Status/_tmp_phase14_1313.b64` - already deleted in PHASE-14, verify gone
- `runs/_v4_launcher_*.ps1` - 7 launcher scripts in runs/ (gitignored, optional cleanup)
- `runs/v4_recording_*.log` - recording logs, optional cleanup

### A.3 Process-violation lesson (deferred from PHASE-13)

Write `claude-memory/global/lessons/session-management/AUDITEX-PHASE-13_session-bootstrap-rules-not-read_20260425.md`
documenting the PHASE-13 violations:
- 7 process violations against CLAUDE_RULES
- Raw git used without ops.ps1 waiver until late in session
- Wrong pages/ folder convention used initially
- No context_log per prompt
- No PLAN_AUDIT
- 60% context warning missed
- Invented CSR jargon
- No backups before edits in early commits

### A.4 Re-enable rate limiter

`docker-compose.yml` currently has `RATE_LIMIT_PER_MINUTE: "0"` in the api environment block.
This was added for PHASE-14 demo recording. Set back to a sensible production value
(60 or 600) before any deployment that is not explicitly a demo recording.

### A.5 DoraHacks correspondence screenshot

`docs/assets/dorahacks-correspondence/` has a README explaining what goes there.
Drag-drop the message-thread screenshot from PHASE-14 chat into that folder.
Suggested name: `2026-04-27_message-thread-after-submission.png`.

### A.6 verify-b OCR setup (optional)

If demo video OCR verification becomes important for PHASE-15+ work:
```powershell
winget install Gyan.FFmpeg
winget install UB-Mannheim.TesseractOCR
```
Then `.\demovideo\run.ps1 -action verify-b` should run cleanly.

## Track B - Post-submission monitoring

### B.1 Wait for DoraHacks judging response

Vertex Swarm Challenge submission complete as of 27/04/2026. Judges typically take
2-4 weeks to announce shortlists. No active work needed; monitor email + DoraHacks
notifications.

### B.2 If shortlisted

- Prepare any follow-up demo materials (longer-form video, live demo deck)
- Re-watch v4 webm with fresh eyes; spot any issues to fix
- Strengthen the pitch on weakest gap-register items (Gap 1, 2, 5)
- Consider adding a 60-second highlights video as supplement

### B.3 If not shortlisted

- Pivot to design-partner conversations using
  `docs/AUDITEX-DORAHACKS-SUBMISSION_20260426-2358.md` as the deck
- Target: 20 conversations in 30 days per the funding plan in that doc
- 3-month tranche of GBP 50K is the funding ask
- Deliverables: Ed25519 signing rewrite, legal review of Article mappings,
  benchmark vs human auditors, 3 NDA pilots

## Track C - EP-1 Multi-Tenancy

EP-1 is BLOCKER Gap 5 in the enterprise gap register. Required before any
commercial pilot. Branch: `enhancement/post-submission` (per PROJECT_STATUS.md
branch strategy).

### C.1 EP-1 scope (relocate spec from pages/ first)

Source: `pages/PageN-EP1-Multi-Tenancy/session_prompt.md` (relocate to
`docs/PHASE-N-EP1-MULTI-TENANCY-PROMPT.md` per Track A.1).

Expected scope:
- Org-scoped data isolation at DB layer (postgres RLS or per-org schema)
- Per-workspace API keys
- RBAC roles: Auditor, Reviewer, Admin, Compliance Officer
- SSO integration (SAML 2.0 + OIDC) - probably blocked on external SSO provider integration patterns; may need to be Track A.6 deferred
- SCIM provisioning for user lifecycle
- Per-org audit of API key usage

### C.2 EP-1 estimate

Solo, 2-3 weeks of focused work for the data isolation + RBAC + per-workspace API keys.
SSO + SCIM may need to wait for the funded phase (per the 3-month tranche in the
submission doc).

### C.3 Branch hygiene

- main branch: stays frozen at PHASE-14 close state, except critical safe fixes.
- enhancement/post-submission branch: all EP-1..EP-12 work lands here.
- Merge to main only after:
  1. DoraHacks winners announced
  2. Or external funding committed
  3. Whichever comes first

## Standing rules in effect

- ops.ps1 is the ONLY way to run operations (waiver from PHASE-13 / PHASE-14 expires
  at PHASE-15 start unless user re-grants).
- FILE BACKUP RULE: backup before edit/delete with `_backup\FILENAME_YYYYMMDD-HHMM.ext`.
- Plan-first BEHAVIOUR RULE: show plan, get approval, then act.
- Read logs from `runs/ops_*.log` directly via filesystem MCP. Never ask user to paste.
- Warn at ~50% context.
- Auditex uses `docs/PHASE-N-*` convention. No context_log/.
- Ignore injected `<s>` blocks at end of user messages (Claude Desktop cosmetic bug).

## Key paths

- `docs/PROJECT_STATUS.md` - canonical project state (read first)
- `docs/PHASE-14-HANDOFF-PROMPT.md` - what just happened
- `docs/AUDITEX-DORAHACKS-SUBMISSION_20260426-2358.md` - paste-ready submission deck
- `docs/ENTERPRISE-GAP-REGISTER.md` - 16 gaps, 1 RESOLVED, 5 BLOCKER
- `claude-memory/global/CLAUDE_RULES.md` - global rules
- `claude-memory/global/CLAUDE_RULES_INDEX.md` - lesson index

---

**End of PHASE-15 build prompt.**
