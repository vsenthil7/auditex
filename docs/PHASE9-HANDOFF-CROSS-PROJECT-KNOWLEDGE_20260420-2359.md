# AUDITEX — PHASE 9 HANDOFF: Cross-Project Knowledge Transfer from TNPE2026

**Date written:** 2026-04-20 23:59 UK
**Written by:** Claude (same Claude that was running the TNPE2026 project at BLD-034 close)
**Companion to:** `PHASE9-HANDOFF-PROMPT.md` (the existing Phase 9 handoff written 2026-04-06 16:54)
**How to use:** Paste BOTH files into the new Phase 9 session — the existing handoff for the Auditex-specific next-tasks + this file for transferable discipline, CSR methodology, and new rules that emerged between 2026-04-06 and 2026-04-20.

---

## WHY THIS FILE EXISTS

Between 2026-04-06 (Phase 8 close) and 2026-04-20 (now), I spent ~15 sessions on the TNPE2026 / TalkProof project. During that run, several discipline patterns, rule refinements, and a complete **Close-Session Ritual (CSR) tooling MVP** were built. Many of those are **global dev-discipline** and apply cleanly to Auditex too. A few are TNPE2026-specific (different ops.ps1 action set, different naming hierarchy, different stack) and are NOT brought forward here.

This file is the transfer. Read it once before starting Phase 9 if you want the benefit; ignore it if you prefer not to change Auditex rhythms mid-project.

---

## HACKATHON DATE — CHECK BEFORE WORK STARTS

User flagged at 2026-04-20 23:55: "date of the hack change to 22/04 10:00 (dont know the timing what they mean Singaporian or anythign else go through the assessment page u will link to the hack in dora)."

**Master Brief in `doc/Hack0014-Vertex-Swarm-Challenge-Master-Brief.md` (dated 04/04/2026 17:10) says submission deadline is April 6, 2026.** That was written at Phase 0. The date appears to have shifted to **22 April 2026, 10:00** — timezone unknown (likely SGT since Tashi is Singapore-based, but verify).

**Before doing any build work, open the DoraHacks Hack0014 page and confirm:**
1. Exact submission deadline date + time
2. Timezone (SGT / UTC / local)
3. Any other terms that changed (prize pool, tracks, team size — Master Brief flagged Rules tab says 5, FAQ says 3)

If deadline is 22/04 10:00 SGT = 02:00 UTC = 03:00 UK (BST). Roughly **1.5 days from now** if UK time. Plan accordingly.

---

## FOLDER NAME NOTE

The original Phase 0 `BUILD-PROMPT-PHASE0-POC-ENGINE.md` referenced `poc-engine/` as the project workspace folder. The actual folder that got built is `auditex/`. Not a blocker — just a rename that happened between spec and build. Phase 9 handoff and PROJECT_STATUS both use `auditex/`. Nothing to do.

---

## SECTION 1 — CSR (CLOSE-SESSION RITUAL): TWO WAYS I DO IT

CSR = what I produce at the end of every work block / session so the next session (or the next person) can pick up without context loss. Auditex already has a lightweight version — `MEMORY.md` and `PROJECT_STATUS.md` updated at end of every work block. The patterns below are complementary.

### 1a. Old way (tier-0) — manual, ~20-30 min per close

Produce two documents at session end:

**DONE file** — what got done:
- HEADLINE (2-3 sentences: key outcome)
- COMMITS LANDED (git log --oneline range for the session)
- WHAT GOT DONE (chronological bullet list, tied to commits)
- TEST STATUS (pass count, coverage, delta vs session start)
- NEW LESSONS SURFACED (pointers to lesson files, not bodies)
- RULE COMPLIANCE SUMMARY (did plan-first hold? commit-first? any violations?)
- NOT DONE / DEFERRED (carry-forward items for next session)

**DEVIATION file** — plan vs reality:
- PLAN VS DELIVERED (table: each planned unit → delivered / partial / not done, with commit refs)
- SCOPE STRETCHES (any unit added outside original plan — and the user's approval for it)
- RULE COMPLIANCE (mechanical audit: git-add-files usage count, raw-git count, backup evidence, plan-first mentions)
- CARRY-FORWARD PATTERNS (open items + next-planned bullets from session)
- DEVIATION NARRATIVE (200-400 word prose: what went well, what didn't, patterns to carry forward)

These two files go into `session_prompts/` (or the project's equivalent; Auditex uses `docs/PHASE-N-HANDOFF-PROMPT.md` which serves a similar function).

For Auditex, the equivalent lean structure is already what's in `MEMORY.md` + `PROJECT_STATUS.md` + phase handoff prompts. You do not need separate DONE + DEVIATION files unless you want the separation. The key principle: **session N+1 can pick up without reading session N chat transcript**.

### 1b. Scripted way (tier-1) — what I planned to adopt, ~5-10 min per close

I built a set of scripts at TNPE2026 that automate the mechanical parts of CSR (reading git state, counting tests, extracting commits, aggregating carry-forwards). They leave only the judgement parts to Claude (headline wording, rule-compliance verdict, narrative prose). Breakdown:

- `csr-collect-state.ps1` — captures git HEAD + dirty state + last test logs' pass/fail/coverage numbers into a YAML state file
- `csr-assemble-done.py` — reads YAML + context_log directory → emits DONE.md with 3 AI-filled placeholders (HEADLINE, RULE COMPLIANCE SUMMARY, PRODUCT-LEVEL SIGNIFICANCE)
- `csr-assemble-deviation.py` — reads same inputs + START file → emits DEVIATION.md with 1 AI-filled placeholder (DEVIATION NARRATIVE)
- `csr-close.ps1` — orchestrator that runs the three in sequence

**Status as of 2026-04-20:** All 4 scripts exist and run. 137 pytest + 33 PS smoke passing. Real third-dogfood validation at BLD-034 exposed a parse-gap (fix-1-partial on one START format) — filed for next session. Net verdict: the scripts save **~10 minutes wall-clock per CSR** when everything works, and they force a single consistent shape across sessions.

**Should you port this to Auditex?** Probably not for this project.
- Reason 1: You are inside a hackathon finishing-line sprint (deadline 22/04 10:00). Adopting a new toolchain mid-sprint is not the best trade.
- Reason 2: Auditex's existing rhythm (MEMORY.md + PROJECT_STATUS.md + phase handoffs) already does ~70% of what the scripts do. You would be replacing 30-min manual effort with a 1-hour tool build + learning curve.
- Reason 3: The scripts are opinionated toward a `session_prompts/` + `plan_audit/` + `context_log/` folder layout that Auditex doesn't have. Adopting them = restructuring paths.

**What to do instead for Auditex Phase 9:** keep current methodology. If post-hack you want to port the scripts, they live in `C:\Users\v_sen\Documents\Projects\0002_AT_TNPE2026_TamilNaduPoliticsElection2026\AT_TNPE2026_004_APPDEV-CampaignVoiceApp\talkproof_dev\scripts\csr\`.

---

## SECTION 2 — NEW DISCIPLINE RULES (transferable to Auditex)

These are global dev-discipline rules that landed during TNPE2026 BLD-033 and BLD-034. Each is marked:
- **[GLOBAL]** = applies to any project, consider for Auditex
- **[TNPE2026-ONLY]** = project-specific, NOT ported
- **[OPTIONAL]** = you decide

### Rule A [GLOBAL] — Context-log-per-prompt

At the start of every prompt-response cycle, write a short record of what the user asked + what you'll do. Purpose: an audit trail Claude N+1 can read even if chat history is lost. Format: one file per prompt, numbered, timestamped, in a `context_log/` folder at the page/session level.

**For Auditex:** light version — update `MEMORY.md` at the end of every work block (already done). You do not need a separate per-prompt log if you maintain MEMORY.md diligently. Full version if you want stricter audit: add a `docs/context_log/` folder.

### Rule B [GLOBAL] — "Lesson from previous prompt" header

Second section of every context_log file is `## LESSON FROM PREVIOUS PROMPT` — 2-3 sentences on what the last interaction taught. Makes lesson-surfacing a by-product of the work, not a retroactive session-close chore.

**For Auditex:** adoption optional. If you maintain MEMORY.md well, lessons already land there. If you want them machine-extractable later, put a distinct heading.

### Rule C [GLOBAL] — Shell `date` at start AND end of every response

Run `Get-Date -Format 'yyyy-MM-dd HH:mm:ss (dddd) UK'` at the start and end of every response. Output visible in chat. Auditable timestamping that doesn't rely on Claude's interpreted-time guesses (which drift). Extra discipline credit when `date` runs at every CSR step.

**For Auditex:** strongly recommend. Zero cost, full audit value. Adopt immediately.

### Rule D [GLOBAL] — No deletions; move to `_backup/<reason>/`

When a file is judged wrong or superseded, do NOT `Remove-Item`. Move to `_backup/<reason>/` with a README that explains what was there and why it moved. Preserves audit trail.

**For Auditex:** adopt. Trivial cost. Many files get written mid-hack that later turn out wrong — keep them as evidence.

### Rule E [GLOBAL] — "Lean" means my AI effort, NOT audit output

When optimising CSR cost: lean = fewer tool calls, less Claude thinking, batched edits. Lean is NEVER shorter audit deliverables. Audit content stays comprehensive; Claude's effort-per-unit-of-output drops.

**For Auditex:** applies to MEMORY.md + PROJECT_STATUS.md — keep them comprehensive even when sessions are rushed.

### Rule F [GLOBAL] — Plan-first (no code before plan approved)

Every P0 unit of work gets a plan written to an audit folder BEFORE any code edit. User approves. Then action. Streak discipline — count consecutive sessions with plan-first held.

**For Auditex:** already encoded in existing standing rules ("one step at a time"). No change needed.

### Rule G [GLOBAL] — COMMIT-FIRST

Write → commit → push → THEN test. Never stack uncommitted changes. If test fails: next commit contains the fix, not a revert. Prevents lost work on crash.

**For Auditex:** already encoded. No change needed.

### Rule H [GLOBAL] — File-backup before edit

For any file >20KB or any file that's hard to recreate, copy to `_backup/<filename>_<timestamp>` before editing. Read-back verify the backup exists before the edit. For files tracked in git, git IS the backup — no explicit copy needed.

**For Auditex:** apply to MEMORY.md + PROJECT_STATUS.md + docker-compose.yml + any `.env` file. They're either not in git or too destructive to lose.

### Rule I [TNPE2026-ONLY] — `ops.ps1` as only operations interface

TNPE2026 has a large `ops.ps1` with 40+ actions (docker, git, admin, flutter, test, migrate, etc). Rule: never run raw git/docker — always via ops.ps1.

**For Auditex:** Auditex has its own `ops.ps1` with `action`-style dispatch (git, playwright, status, celery-logs, diag, clear). Keep using it that way. The rule transfers; the specific action set does not.

### Rule J [TNPE2026-ONLY] — 4-level naming hierarchy

TNPE2026 uses a strict 4-level folder naming standard (Project Root / Workstream / Topic / Page). Not applicable to Auditex which has a flatter structure.

**For Auditex:** skip.

### Rule K [GLOBAL] — 99% coverage floor / 100% target

Test coverage never drops below 99% per suite. 100% is aspirational. If coverage would drop, add tests before shipping.

**For Auditex:** already met on Playwright (11/11). If backend unit tests are added in Phase 9+, apply same rule.

### Rule L [GLOBAL] — No scope shrink at plan time

If a phase cannot fit a session, declare overflow honestly at block exit and defer. Never pre-cut scope during planning to make it "fit."

**For Auditex:** matches existing "no scope shrink" rule. Already encoded.

### Rule M [GLOBAL] — Honest misattribution recovery

If you (Claude) claim user did X and user says "I didn't" — retract cleanly, say mechanism unclear, don't invent a plausible story. Default when ambiguous: "unattributed, mechanism unknown" rather than guess.

**For Auditex:** adopt. Matters more in audit-grade products (Auditex literally ships audit features, so meta-audit discipline should be highest here).

---

## SECTION 3 — TRANSFERABLE ENGINEERING LESSONS FROM TNPE2026

These are non-rule lessons that emerged from doing the work. Relevance-to-Auditex flagged per lesson.

### L1 — Widen regex against REAL data, not reference fixtures

At BLD-034 I wrote a regex to match session-unit headings. Built the regex against BLD-033's fixture (which used `UNIT A` letter-IDs) and unit-tests all passed. Dogfooded against BLD-034's own session — same regex, different real heading (`SOLE UNIT (P0)`) → zero match. The fix shipped unit-test-green but broke on real data.

**Auditex analogue:** when you write any parser / extractor (task-status regex, Playwright log parser, document-classification pattern), validate against multiple real samples, not just the one that inspired the fix.

### L2 — Audit-trail discipline degrades first under context pressure

At BLD-034 with context ~85% full, I dropped: (a) writing context_log per prompt, (b) matching the user's format-template when one was attached, (c) checking pre-existing folders before creating new ones. What I DID keep under pressure: commit-first, file-backup, plan-first. The pattern: under load, code-safety rules hold, audit-trail rules slip.

**Auditex analogue:** hackathon deadline is a pressure event. Expect the same LLM degradation. Mitigation: Rule C (shell date every response) is a cheap forcing-function because it's so visible. If it's missing from a response you can see discipline slipping immediately.

### L3 — MCP outages happen periodically (~4h)

On BLD-034 the Claude Desktop MCP servers (filesystem + shell) went unresponsive twice, ~4 hours apart. Each time: tool calls report 4-minute timeout; work often lands server-side anyway but client has no confirmation. Pattern may recur.

**Auditex analogue:** same toolchain, same risk. Recovery: after any MCP outage, verify disk state via `git status` + re-read affected files before replaying any edit.

### L4 — Python inline command-line has Windows length limits

`python -c "<long script>"` hits Windows CMDLINE max and fails. Fix: write a temp `_tmp_*.py` file, run it, delete (or move to backup per Rule D).

**Auditex analogue:** any Python-one-liner > ~1000 chars should be a file.

### L5 — Long paths need `git config --global core.longpaths true`

Windows MAX_PATH of 260 chars is the default; nested project folders + timestamped backups quickly exceed it. Global git config plus `\\?\` prefix on Copy-Item are needed.

**Auditex analogue:** already possibly an issue if `runs/` accumulates many timestamped logs. Check with `(pwd).Path.Length` and total longest-path; add the git config if not already set.

### L6 — Dual-methodology during tool migration

When replacing a manual process (tier-0) with a scripted one (tier-1), run BOTH in parallel for a period until the scripted one is proven in real use. At TNPE2026 this decision was made 2 sessions after the scripts were "done" — correct call, because a parse-gap surfaced only in the parallel run.

**Auditex analogue:** if you add automation (e.g. a Playwright-runner wrapper, a report-generator) in Phase 9+, keep the manual fallback until you have 3-5 clean runs of the automated one.

---

## SECTION 4 — MEMORY FILES TO NOT CONFUSE

Claude has multiple "memory" files with different scopes. Don't let these get crossed:

- `C:\Users\v_sen\Documents\Projects\claude-memory\global\CLAUDE_RULES.md` — **global Claude rules, all projects**. Phase 9 handoff already tells you to read this first. Good.
- `C:\Users\v_sen\Documents\Projects\claude-memory\global\PROJECT_STATUS.md` — **cross-project status across ALL Claude's work**. Not Auditex-specific.
- `C:\Users\v_sen\Documents\Projects\0001_Hack0014_Vertex_Swarm_Tashi\auditex\docs\MEMORY.md` — **Auditex project memory**. This is your working memory file.
- `C:\Users\v_sen\Documents\Projects\0001_Hack0014_Vertex_Swarm_Tashi\auditex\docs\PROJECT_STATUS.md` — **Auditex project status**. This is your working status file.

Auditex-internal memory updates: edit `auditex/docs/MEMORY.md` + `auditex/docs/PROJECT_STATUS.md` only. Do NOT touch `claude-memory/global/*` from inside Auditex sessions — that's cross-project state and a wrong edit there corrupts TNPE2026 too.

---

## SECTION 5 — QUICK-START CHECKLIST FOR PHASE 9 OPEN

If you only read one section of this handoff, this is it:

1. `Get-Date -Format 'yyyy-MM-dd HH:mm:ss (dddd) UK'` — RULE C
2. Read `claude-memory/global/CLAUDE_RULES.md` (per existing Phase 9 handoff)
3. Read `auditex/docs/PROJECT_STATUS.md` (per existing Phase 9 handoff)
4. Read `auditex/docs/PHASE9-HANDOFF-PROMPT.md` — original handoff tasks (TASK 1..5)
5. Verify hackathon deadline on DoraHacks — is it still 06/04 or now 22/04 10:00 SGT? (CRITICAL)
6. Run the 5 tasks from the original handoff (git commit, celery rebuild, playwright, log read, proceed with Phase 9)
7. At the END of the work block: `Get-Date` again + update MEMORY.md + PROJECT_STATUS.md — RULE C + existing Auditex pattern
8. If work block was long enough to warrant a handoff: write `PHASE9-<n>-HANDOFF.md` in `auditex/docs/` with: git commit range, test status, what's pending, what to do first next session

---

## SECTION 6 — HOW TO USE THIS FILE

You now have TWO files to paste into the new Phase 9 session:

1. `docs/PHASE9-HANDOFF-PROMPT.md` — the Auditex-specific next-tasks (already existed)
2. `docs/PHASE9-HANDOFF-CROSS-PROJECT-KNOWLEDGE_20260420-2359.md` — THIS file (transferable discipline from TNPE2026)

**Recommended paste order:** THIS file first, then the existing one. That way Claude opens the session with discipline rules loaded, then reads the Auditex-specific tasks.

If time is tight: paste only the existing one. This file is a nice-to-have, not a blocker.

---

**End of cross-project knowledge transfer handoff. Good luck on the hackathon.**
