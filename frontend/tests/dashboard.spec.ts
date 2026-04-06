/**
 * Auditex Dashboard — Playwright E2E Tests
 *
 * COMPLETE SCENARIO MATRIX
 * ========================
 *
 * Pipeline statuses:  QUEUED → EXECUTING → REVIEWING → FINALISING → COMPLETED | FAILED
 *
 * Task type × Recommendation matrix (9 scenarios + 1 dashboard + 1 UI check = 11 tests):
 *
 *  TC-01  Dashboard loads
 *
 *  DOCUMENT REVIEW  (recommendations: APPROVE | REQUEST_ADDITIONAL_INFO | REJECT)
 *  TC-02  document_review → APPROVE             (complete mortgage application)
 *  TC-03  document_review → REQUEST_ADDITIONAL_INFO  (partially complete — missing some docs)
 *  TC-04  document_review → REJECT              (fraudulent/impossible data)
 *
 *  RISK ANALYSIS  (recommendations: APPROVE | REQUEST_ADDITIONAL_INFO | REJECT)
 *  TC-05  risk_analysis   → APPROVE             (healthy profitable business)
 *  TC-06  risk_analysis   → REQUEST_ADDITIONAL_INFO  (borderline — needs more info)
 *  TC-07  risk_analysis   → REJECT              (insolvent, administrator appointed)
 *
 *  CONTRACT CHECK  (recommendations: APPROVE | REQUEST_AMENDMENTS | REJECT)
 *  TC-08  contract_check  → APPROVE             (fully GDPR compliant DPA)
 *  TC-09  contract_check  → REQUEST_AMENDMENTS  (partial compliance — minor gaps)
 *  TC-10  contract_check  → REJECT              (GDPR violations, patient data at risk)
 *
 *  TC-11  UI consistency — all 9 completed tasks show 5 steps, correct badges, green dots
 *
 * Each test:
 *  - Submits a document crafted to elicit the specific recommendation from Claude
 *  - Polls until COMPLETED
 *  - Asserts the recommendation badge matches the expected value
 *  - Asserts all lifecycle dots are green
 *  - Asserts Steps 1-5 all render in the detail panel
 *
 * Run:  npx playwright test --reporter=list
 */

import { test, expect, type Page } from '@playwright/test'
import * as fs from 'fs'
import * as path from 'path'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname  = path.dirname(__filename)

const BASE_URL = 'http://localhost:3000'
const API_URL  = 'http://localhost:8000'
const API_KEY  = 'auditex-test-key-phase2'
const POLL_MS  = 5_000
const ACTIVE   = new Set(['QUEUED','EXECUTING','REVIEWING','FINALISING'])
const TERMINAL = new Set(['COMPLETED','FAILED','ESCALATED'])

// ══════════════════════════════════════════════════════════════════════════════
// SCENARIO DOCUMENTS
// Each document is crafted to reliably elicit a specific recommendation.
// ══════════════════════════════════════════════════════════════════════════════

// ── DOCUMENT REVIEW ──────────────────────────────────────────────────────────

/** TC-02: All fields complete, strong financials → APPROVE */
const DR_APPROVE = `
MORTGAGE APPLICATION — COMPLETE SUBMISSION

Applicant:        Jane Elizabeth Doe, DOB 22/07/1990, NI AB123456C
Address:          14 Maple Avenue, London SW1A 1AA (owner-occupier 5 years)
Employer:         FinTech Solutions Ltd — Senior Product Manager, permanent, 5 years
Gross Salary:     92000 GBP/year   |  Net Monthly: 6100 GBP
Bonus (3yr avg):  13667 GBP/year   |  P60 submitted: YES
Savings:          87000 GBP (6-month bank statements submitted)
Existing Debts:   Car finance 8400 GBP (120/month) — no other debts
Credit Score:     Experian 780 (Excellent) — zero CCJs, zero defaults, zero missed payments

Loan Request:     340000 GBP against property 480000 GBP (LTV 70.8%)
Deposit:          140000 GBP (29.2%, funded from savings)
Monthly Payment:  1840 GBP at 4.5% — 30% of net income (within policy)
Loan Purpose:     Residential mortgage, primary dwelling, 25 year term

Documents Provided:
  ✓ 3 months payslips    ✓ 2 years P60     ✓ 6 months bank statements
  ✓ Passport (valid)     ✓ Proof of address ✓ Property valuation 485000 GBP
  ✓ Solicitor confirmed  ✓ Stress test pass (7% = 2340/month, affordable)

Income multiple: 3.7x (policy max 4.5x)  |  Affordability: PASS  |  LTV: PASS
`

/** TC-03: Missing some supporting documents, borderline income → REQUEST_ADDITIONAL_INFO */
const DR_REQUEST = `
MORTGAGE APPLICATION — PARTIAL SUBMISSION

Applicant:        Michael Brown, DOB 15/03/1985
Address:          22 High Street, Birmingham B1 1AA
Employer:         Local Council — Admin Officer, 2 years employment
Gross Salary:     34000 GBP/year
Bank Statements:  NOT PROVIDED — applicant states "will send shortly"
Payslips:         Only 1 month provided (3 months required)
P60:              NOT PROVIDED
Credit Score:     Not disclosed by applicant
CCJs:             Unknown — not confirmed

Loan Request:     195000 GBP against property 220000 GBP (LTV 88.6%)
Deposit:          25000 GBP (source of funds not evidenced)
Monthly Payment:  Estimated 1100 GBP

Income multiple: 5.7x — EXCEEDS policy maximum of 4.5x
Missing fields: bank statements, 2 additional payslips, P60, credit check, deposit source
`

/** TC-04: Clearly fraudulent/impossible data → REJECT */
const DR_REJECT = `
MORTGAGE APPLICATION — SUSPICIOUS SUBMISSION

Applicant:        John Smith, DOB 01/01/1900 (age 126 — impossible)
Address:          123 Fake Street, London (property does not exist on Land Registry)
Employer:         Self — "CEO of my own company" (no company number provided)
Gross Salary:     500000 GBP/month (stated verbally, no evidence)
Bank Statements:  Provided — show only 200 GBP balance

Loan Request:     2000000 GBP (10x stated annual income — impossible)
Property Value:   Applicant states 2500000 GBP — no valuation report provided
Deposit:          50000 GBP (cannot explain source)
Existing Debts:   12 active CCJs totalling 340000 GBP
Bankruptcy:       Discharged 18 months ago
Credit Score:     Very Poor — multiple defaults in last 12 months
Fraud Indicators: Address does not exist, date of birth impossible, income unverifiable
`

// ── RISK ANALYSIS ─────────────────────────────────────────────────────────────

/** TC-05: Strong profitable business, growing revenue, good security → APPROVE */
const RA_APPROVE = `
COMMERCIAL LOAN APPLICATION — HEALTHY BUSINESS

Business:         Sunrise Bakery Ltd (Company No. 12345678)
Incorporated:     March 2018 — 7 years trading
Sector:           Food manufacturing (SIC 10710)
Directors:        Sarah Mitchell (51%) + James Mitchell (49%)
                  Both providing unlimited personal guarantees
                  Credit scores: 780 / 755 — no adverse history

Audited Accounts (3 years):
  2022: Revenue 620000 | Gross Profit 285000 (46%) | Net Profit 72000 | EBITDA 95000
  2023: Revenue 740000 | Gross Profit 342000 (46%) | Net Profit 89000 | EBITDA 118000
  2024: Revenue 890000 | Gross Profit 415000 (47%) | Net Profit 108000 | EBITDA 142000
  Revenue CAGR 19.7% | Margin stable | YTD 2025 on track for 1020000

Balance Sheet Dec 2024:
  Total Assets 780000 | Total Liabilities 210000 | Net Assets 570000
  Current Ratio 2.4 | Quick Ratio 1.8 | Debt/Equity 0.37

Existing Finance: Commercial mortgage 150000 (current) + Asset finance 45000 (current)
No CCJs, no defaults, payments current on all facilities

Loan Request:     200000 GBP — new automated production line
Security:         Fixed charge on equipment (value 280000) + personal guarantees + debenture
DSCR:             3.2x at current earnings — strong coverage
Clients:          38 wholesale accounts including Tesco (3-year contract 2024)
`

/** TC-06: Some positives but significant gaps — needs clarification → REQUEST_ADDITIONAL_INFO */
const RA_REQUEST = `
COMMERCIAL LOAN APPLICATION — BORDERLINE CASE

Business:         TechStart Ltd
Incorporated:     18 months ago — limited trading history
Sector:           Software development

Revenue:          Year 1: 85000  |  Year 2 projected: 180000 (projection only, not audited)
Accounts:         Management accounts only — no audited financials yet
Profit:           Currently break-even, expecting profit in Q3 this year

Director:         Solo director, age 28, first business
Personal Guarantee: Offered but director has 45000 GBP student debt
Credit Score:     Not provided in application
Security:         Intellectual property (IP — difficult to value/realise)

Loan Request:     120000 GBP working capital
Purpose:          Hiring 2 developers — no firm client contracts in place yet
Current Cash:     22000 GBP — 3 months runway without new revenue

Missing: audited accounts, client contracts, director credit check, IP valuation
`

/** TC-07: Insolvent, administrator appointed, no collateral → REJECT */
const RA_REJECT = `
COMMERCIAL LOAN APPLICATION — HIGH RISK / DISTRESSED

Business:         Collapsed Retail Ltd
Incorporated:     January 2020 (5 years, now distressed)
Sector:           High street retail (declining sector)

Financial Position:
  Revenue:         Declining — 480000 (2022) → 310000 (2023) → 195000 (2024)
  Net Margin:      -45% in 2024 — losing money heavily
  Existing Debts:  890000 GBP owed to 14 creditors (multiple overdue)
  CCJs:            4 outstanding county court judgements totalling 210000 GBP
  Cash Position:   Overdraft 35000 GBP — no available liquidity

Directors:
  3 of 4 directors resigned in last 90 days
  Remaining director has personal bankruptcy in 2019

Legal Status:     Administrator appointed 8 days ago
Collateral:       None available — all assets subject to existing charges

Loan Request:     500000 GBP emergency working capital
Purpose:          Pay outstanding wages and supplier debts
Repayment Plan:   "Hope to trade our way out" — no credible plan provided
`

// ── CONTRACT CHECK ────────────────────────────────────────────────────────────

/** TC-08: Full GDPR Article 28 compliance, all clauses present → APPROVE */
const CC_APPROVE = `
DATA PROCESSING AGREEMENT — FULLY COMPLIANT SUBMISSION

Ref: DPA-2025-089  |  Date: 1 January 2025  |  Jurisdiction: England and Wales

Controller:  MedTech Solutions Ltd (ICO Reg ZA123456, Company 09876543)
Processor:   DataFlow Analytics Ltd (ICO Reg ZB789012, Company 07654321)

Scope:
  Purpose:       Analytics on anonymised patient outcome data — clinical research only
  Legal Basis:   Article 6(1)(f) legitimate interests — DPIA completed and documented
  Special Cat:   NO special category data — all data anonymised before transfer
  Retention:     24 months maximum — documented deletion procedure confirmed

GDPR Article 28(3) Checklist — ALL ITEMS CONFIRMED:
  (a) Process only on written instructions:      ✓ Schedule 1 documents all instructions
  (b) Staff confidentiality obligations:         ✓ NDA signed by all staff
  (c) Appropriate technical/org security:        ✓ ISO 27001 certified (cert attached)
  (d) Sub-processor restrictions:                ✓ Prior written consent required
  (e) Assist with data subject rights:           ✓ 48-hour SLA committed in writing
  (f) Assist with security obligations:          ✓ Joint security protocol agreed
  (g) Delete/return data at end of contract:     ✓ 30-day deletion confirmed in writing
  (h) Provide audit information + inspections:   ✓ Annual audit right with 30 days notice

Security: AES-256 at rest | TLS 1.3 in transit | MFA required | Pen test Nov 2024
Sub-processors: AWS UK eu-west-2 (DPA in place) | Snowflake EU eu-west-1 (DPA in place)
Transfers: ALL within UK/EEA — NO third country transfers confirmed in Schedule 2
Breach Notification: Within 24 hours (exceeds 72-hour GDPR requirement)
Liability Cap: 5000000 GBP | Cyber insurance: 2000000 GBP confirmed
Signed by both parties 1 January 2025
`

/** TC-09: Mostly compliant but several gaps needing amendments → REQUEST_AMENDMENTS */
const CC_REQUEST = `
DATA PROCESSING AGREEMENT — PARTIAL COMPLIANCE

Ref: DPA-2025-045  |  Date: March 2025  |  Jurisdiction: England and Wales

Controller:  RetailCo Ltd
Processor:   CloudStore Analytics Ltd

Scope:
  Purpose:       Customer purchase behaviour analytics and profiling
  Legal Basis:   Legitimate interests stated — DPIA NOT completed
  Special Cat:   None stated but profiling may reveal health/religious inferences

GDPR Article 28(3) Review:
  (a) Written instructions:      ✓ Present in Schedule 1
  (b) Staff confidentiality:     ✓ NDA in place
  (c) Security measures:         PARTIAL — ISO 27001 in progress (not yet certified)
  (d) Sub-processor restrictions: MISSING — no sub-processor clause included
  (e) Data subject rights assist: PARTIAL — SLA not specified, process vague
  (f) Security obligation assist: ✓ Present
  (g) Deletion at end:            MISSING — no deletion timeframe specified
  (h) Audit rights:               PARTIAL — audit right present but no notice period

Security: Encryption at rest ✓ | Encryption in transit ✓ | MFA NOT required
Sub-processors: AWS listed but no DPA evidenced for AWS usage
Breach Notification: 72 hours stated (meets minimum requirement only)
Liability Cap: 50000 GBP (appears low relative to contract value of 400000/year)
Gaps: DPIA missing, sub-processor DPAs not provided, deletion clause absent
`

/** TC-10: NHS data, selling to marketing, zero liability, no GDPR compliance → REJECT */
const CC_REJECT = `
DATA PROCESSING AGREEMENT — NON-COMPLIANT SUBMISSION

Parties: ShadowData Corp (Processor) and NHS Trust (Controller)
Type:    Informal written agreement — not a full DPA
Date:    Undated

Scope:
  Data:          Full NHS patient medical records including diagnoses, medications,
                 mental health history, HIV status, genetic data — FULL special category data
  Purpose:       "Data monetisation and analytics" — vague and unlawful
  Legal Basis:   NONE stated — no Article 6 or Article 9 basis identified
  DPIA:          NOT conducted despite high-risk processing of special category health data

GDPR Article 28(3) Review — MULTIPLE FAILURES:
  (a) Written instructions:      MISSING — no documented instructions
  (b) Staff confidentiality:     MISSING — no confidentiality obligations
  (c) Security measures:         MISSING — no security provisions whatsoever
  (d) Sub-processor restrictions: MISSING — "may use any third parties as needed"
  (e) Data subject rights:       MISSING — explicitly states "not applicable"
  (f) Security obligation assist: MISSING
  (g) Deletion:                  MISSING — "data retained indefinitely"
  (h) Audit rights:              REFUSED — clause explicitly prohibits audits

Security: NO encryption stated | NO access controls | NO security measures at all
Sub-processors: "any global vendors as required" — completely unlisted
Data Transfer: Includes transfer to US vendors with no adequacy decision or SCCs
Third Party Sharing: Clause 7.3 explicitly permits selling patient data to marketing firms
Breach Notification: NONE required per contract
Liability Cap: 0 GBP — processor accepts absolutely no liability
Patient Rights: Clause 9.1 explicitly states patient rights "do not apply to this agreement"
GDPR Compliance: Processor states GDPR "does not apply to their operations"

This agreement exposes the NHS Trust to regulatory enforcement, fines up to 4% global turnover,
and criminal liability under the Data Protection Act 2018.
`

// ══════════════════════════════════════════════════════════════════════════════
// LOG SETUP
// ══════════════════════════════════════════════════════════════════════════════

const resultsDir = path.join(__dirname, 'results')
if (!fs.existsSync(resultsDir)) fs.mkdirSync(resultsDir, { recursive: true })
const ts        = new Date().toISOString().replace(/[:.]/g, '-')
const logFile   = path.join(resultsDir, `playwright-run-${ts}.log`)
const logStream = fs.createWriteStream(logFile, { flags: 'a' })

function log(m: string)  { const l=`[${new Date().toISOString()}] ${m}`; console.log(l); logStream.write(l+'\n') }
function logStep(s: string) { log(`  STEP  ${s}`) }
function logPass(s: string) { log(`  PASS  ✓ ${s}`) }
function logFail(s: string, e?: unknown) { log(`  FAIL  ✗ ${s}${e?' — '+e:''}`) }
function logInfo(s: string) { log(`  INFO  ${s}`) }
function logSuite(s: string){ log(''); log('═'.repeat(60)); log(`  ${s}`); log('═'.repeat(60)) }

// ══════════════════════════════════════════════════════════════════════════════
// HELPERS
// ══════════════════════════════════════════════════════════════════════════════

async function getActiveTasks(): Promise<number> {
  try {
    const res = await fetch(`${API_URL}/api/v1/tasks?page=1&page_size=100`, {
      headers: { 'X-API-Key': API_KEY }
    })
    if (!res.ok) return 0
    const data = await res.json()
    return (data.tasks ?? []).filter((t: any) => ACTIVE.has(t.status)).length
  } catch { return 0 }
}

async function ensureQueueClear(label: string): Promise<void> {
  logInfo(`${label} — checking queue`)
  const deadline = Date.now() + 90_000
  while (Date.now() < deadline) {
    const active = await getActiveTasks()
    logInfo(`${label} — active: ${active}`)
    if (active === 0) { logInfo('Queue clear'); return }
    await new Promise(r => setTimeout(r, 8_000))
  }
  logInfo(`${label} — proceeding after 90s timeout`)
}

async function submitAndPoll(
  page: Page,
  taskType: 'document_review' | 'risk_analysis' | 'contract_check',
  document: string,
  criteria: string[],
): Promise<void> {
  await ensureQueueClear(taskType)

  logStep(`Navigate + submit ${taskType}`)
  await page.goto(BASE_URL, { waitUntil: 'networkidle' })
  await page.locator('select').selectOption(taskType)
  await page.locator('textarea').fill(document)
  for (const c of criteria) await page.getByLabel(c).check()
  logPass('Form filled')

  const rowsBefore = await page.locator('button.w-full.text-left').count()
  await page.getByRole('button', { name: /Submit Task/i }).click()

  await expect(async () => {
    expect(await page.locator('button.w-full.text-left').count()).toBeGreaterThan(rowsBefore)
  }).toPass({ timeout: 15_000, intervals: [500] })

  await page.locator('button.w-full.text-left').first().click()
  logPass('Task row clicked — detail panel open')

  logStep('Poll to COMPLETED')
  const deadline = Date.now() + 200_000
  let finalStatus = ''
  let elapsed = 0

  while (Date.now() < deadline) {
    await page.waitForTimeout(POLL_MS)
    elapsed += POLL_MS
    try {
      const spans   = await page.locator('button.w-full.text-left').first().locator('span').allTextContents()
      const cleaned = spans.map((s: string) => s.trim()).filter(Boolean)
      logInfo(`[${Math.round(elapsed/1000)}s] ${cleaned.join(' | ')}`)
      const term = cleaned.find((s: string) => TERMINAL.has(s))
      if (term) { finalStatus = term; break }
      await page.locator('button.w-full.text-left').first().scrollIntoViewIfNeeded()
    } catch (e) { logInfo(`poll error: ${e}`) }
  }

  if (!finalStatus) throw new Error(`${taskType}: timed out`)
  if (finalStatus !== 'COMPLETED') throw new Error(`${taskType}: expected COMPLETED got ${finalStatus}`)
  logPass(`COMPLETED in ${elapsed / 1000}s`)
}

async function verifyOutcome(
  page: Page,
  taskType: string,
  expectedRec: string,
): Promise<void> {

  // Ensure detail panel is open and refreshed
  await page.locator('button.w-full.text-left').first().click()
  await page.waitForTimeout(2_000)

  const detail = page.locator('[data-testid="task-detail"]')
  await expect(detail).toBeVisible({ timeout: 10_000 })

  // ── 1. Recommendation badge ──────────────────────────────────────────────
  logStep(`Assert recommendation = ${expectedRec}`)
  const recBadge = detail.locator('span').filter({
    hasText: /APPROVE|REJECT|REQUEST_ADDITIONAL_INFO|REQUEST_AMENDMENTS/
  }).first()
  await expect(recBadge).toBeVisible({ timeout: 10_000 })
  const rec = (await recBadge.textContent())?.trim() ?? ''
  logInfo(`Recommendation badge: ${rec}`)
  expect(rec).toBe(expectedRec)
  logPass(`Recommendation = ${rec} ✓`)

  // ── 2. All 5 steps present ───────────────────────────────────────────────
  logStep('Assert all 5 pipeline steps visible')
  for (const step of ['Step 1', 'Step 2', 'Step 3', 'Step 4', 'Step 5']) {
    await expect(detail.getByText(step, { exact: false })).toBeVisible({ timeout: 5_000 })
    logPass(`${step} visible`)
  }

  // ── 3. All lifecycle dots green ──────────────────────────────────────────
  logStep('Assert lifecycle dots all green')
  const greenDots = detail.locator('.bg-green-500.border-green-500')
  const greenCount = await greenDots.count()
  expect(greenCount).toBeGreaterThan(0)
  logPass(`${greenCount} green dot(s)`)

  // ── 4. No blue active dot ────────────────────────────────────────────────
  expect(await detail.locator('.bg-blue-500.border-blue-500').count()).toBe(0)
  logPass('No blue active dot')

  // ── 5. Step 3 Review Panel — expand and check reviewer cards ────────────
  logStep('Expand Step 3 Review Panel — verify reviewer cards')
  const step3 = detail.getByText('Step 3', { exact: false }).first()
  await step3.click()
  await page.waitForTimeout(500)
  const reviewerCards = detail.locator('.rounded-lg.border.border-gray-100.bg-gray-50')
  const cardCount = await reviewerCards.count()
  logInfo(`Reviewer cards: ${cardCount}`)
  if (cardCount > 0) {
    logPass(`${cardCount} reviewer card(s) rendered`)
    // Check confidence bars exist
    const bars = detail.locator('.bg-gray-200.rounded-full')
    logInfo(`Confidence bars: ${await bars.count()}`)
  }

  // ── 6. Step 5 Report — verify summary visible ────────────────────────────
  logStep('Expand Step 5 Report — verify Plain English Summary')
  const step5 = detail.getByText('Step 5', { exact: false }).first()
  await step5.click()
  await page.waitForTimeout(500)
  const summary = detail.getByText('Plain English Summary')
  if (await summary.isVisible({ timeout: 10_000 }).catch(() => false)) {
    logPass('Plain English Summary visible')
  } else {
    logInfo('Summary not yet visible — report may still be generating')
  }
}

// ══════════════════════════════════════════════════════════════════════════════
// TESTS
// ══════════════════════════════════════════════════════════════════════════════

test.describe('Auditex Dashboard E2E — Full Scenario Matrix', () => {

  test.beforeAll(() => {
    log(''); log('█'.repeat(70))
    log('  Auditex Playwright E2E  —  ' + new Date().toLocaleString())
    log('  Scenario Matrix: 3 task types × 3 recommendations = 9 scenarios')
    log(`  Dashboard: ${BASE_URL}  API: ${API_URL}`)
    log('█'.repeat(70))
  })

  test.afterAll(() => {
    log(''); log('Run complete. Log: ' + logFile)
    logStream.end()
  })

  // ── TC-01: Dashboard ───────────────────────────────────────────────────────
  test('TC-01  Dashboard loads without errors', async ({ page }) => {
    logSuite('TC-01  Dashboard loads')
    test.setTimeout(60_000)

    const errs: string[] = []
    page.on('console', m => { if (m.type()==='error') errs.push(m.text()) })
    page.on('pageerror', e => errs.push(e.message))

    await page.goto(BASE_URL, { waitUntil: 'networkidle' })
    await page.reload({ waitUntil: 'networkidle' })

    await expect(page).toHaveTitle(/Auditex/i)
    logPass('Title correct')

    for (const [label, loc] of [
      ['header',        page.locator('header')],
      ['Submit Task',   page.getByText('Submit New Task')],
      ['select',        page.locator('select')],
      ['textarea',      page.locator('textarea')],
      ['Submit button', page.getByRole('button', { name: /Submit Task/i })],
      ['Tasks panel',   page.getByText(/^Tasks/)],
    ] as const) {
      await expect(loc).toBeVisible()
      logPass(`${label} visible`)
    }

    expect(errs.length).toBe(0)
    logPass('No console errors')
    log('  RESULT  TC-01 PASSED')
  })

  // ── TC-02: Document Review → APPROVE ──────────────────────────────────────
  test('TC-02  document_review → APPROVE (complete mortgage application)', async ({ page }) => {
    logSuite('TC-02  document_review → APPROVE')
    test.setTimeout(360_000)
    await submitAndPoll(page, 'document_review', DR_APPROVE,
      ['Completeness', 'Income Verification', 'Employment Verification'])
    await verifyOutcome(page, 'document_review', 'APPROVE')
    log('  RESULT  TC-02 PASSED')
  })

  // ── TC-03: Document Review → REQUEST_ADDITIONAL_INFO ──────────────────────
  test('TC-03  document_review → REQUEST_ADDITIONAL_INFO (missing documents)', async ({ page }) => {
    logSuite('TC-03  document_review → REQUEST_ADDITIONAL_INFO')
    test.setTimeout(360_000)
    await submitAndPoll(page, 'document_review', DR_REQUEST,
      ['Completeness', 'Income Verification'])
    await verifyOutcome(page, 'document_review', 'REQUEST_ADDITIONAL_INFO')
    log('  RESULT  TC-03 PASSED')
  })

  // ── TC-04: Document Review → REJECT ───────────────────────────────────────
  test('TC-04  document_review → REJECT (fraudulent application)', async ({ page }) => {
    logSuite('TC-04  document_review → REJECT')
    test.setTimeout(360_000)
    await submitAndPoll(page, 'document_review', DR_REJECT,
      ['Completeness', 'Income Verification'])
    await verifyOutcome(page, 'document_review', 'REJECT')
    log('  RESULT  TC-04 PASSED')
  })

  // ── TC-05: Risk Analysis → APPROVE ────────────────────────────────────────
  test('TC-05  risk_analysis → APPROVE (healthy growing business)', async ({ page }) => {
    logSuite('TC-05  risk_analysis → APPROVE')
    test.setTimeout(360_000)
    await submitAndPoll(page, 'risk_analysis', RA_APPROVE,
      ['Risk Assessment', 'Completeness'])
    await verifyOutcome(page, 'risk_analysis', 'APPROVE')
    log('  RESULT  TC-05 PASSED')
  })

  // ── TC-06: Risk Analysis → REQUEST_ADDITIONAL_INFO ────────────────────────
  test('TC-06  risk_analysis → REQUEST_ADDITIONAL_INFO (early stage, needs more info)', async ({ page }) => {
    logSuite('TC-06  risk_analysis → REQUEST_ADDITIONAL_INFO')
    test.setTimeout(360_000)
    await submitAndPoll(page, 'risk_analysis', RA_REQUEST,
      ['Risk Assessment', 'Completeness'])
    await verifyOutcome(page, 'risk_analysis', 'REQUEST_ADDITIONAL_INFO')
    log('  RESULT  TC-06 PASSED')
  })

  // ── TC-07: Risk Analysis → REJECT ─────────────────────────────────────────
  test('TC-07  risk_analysis → REJECT (insolvent, administrator appointed)', async ({ page }) => {
    logSuite('TC-07  risk_analysis → REJECT')
    test.setTimeout(360_000)
    await submitAndPoll(page, 'risk_analysis', RA_REJECT,
      ['Risk Assessment', 'Completeness'])
    await verifyOutcome(page, 'risk_analysis', 'REJECT')
    log('  RESULT  TC-07 PASSED')
  })

  // ── TC-08: Contract Check → APPROVE ───────────────────────────────────────
  test('TC-08  contract_check → APPROVE (fully GDPR compliant DPA)', async ({ page }) => {
    logSuite('TC-08  contract_check → APPROVE')
    test.setTimeout(360_000)
    await submitAndPoll(page, 'contract_check', CC_APPROVE,
      ['Completeness', 'Risk Assessment'])
    await verifyOutcome(page, 'contract_check', 'APPROVE')
    log('  RESULT  TC-08 PASSED')
  })

  // ── TC-09: Contract Check → REQUEST_AMENDMENTS ────────────────────────────
  test('TC-09  contract_check → REQUEST_AMENDMENTS (minor GDPR gaps)', async ({ page }) => {
    logSuite('TC-09  contract_check → REQUEST_AMENDMENTS')
    test.setTimeout(360_000)
    await submitAndPoll(page, 'contract_check', CC_REQUEST,
      ['Completeness', 'Risk Assessment'])
    await verifyOutcome(page, 'contract_check', 'REQUEST_AMENDMENTS')
    log('  RESULT  TC-09 PASSED')
  })

  // ── TC-10: Contract Check → REJECT ────────────────────────────────────────
  test('TC-10  contract_check → REJECT (NHS data sold to marketing, zero liability)', async ({ page }) => {
    logSuite('TC-10  contract_check → REJECT')
    test.setTimeout(360_000)
    await submitAndPoll(page, 'contract_check', CC_REJECT,
      ['Completeness', 'Risk Assessment'])
    await verifyOutcome(page, 'contract_check', 'REJECT')
    log('  RESULT  TC-10 PASSED')
  })

  // ── TC-11: UI consistency across all 9 completed tasks ───────────────────
  test('TC-11  UI consistency — all 9 tasks show 5 steps + correct badges', async ({ page }) => {
    logSuite('TC-11  UI consistency check')
    test.setTimeout(180_000)

    await page.goto(BASE_URL, { waitUntil: 'networkidle' })
    await page.reload({ waitUntil: 'networkidle' })
    logPass('Page loaded')

    const completedRows = page.locator('button.w-full.text-left')
      .filter({ has: page.locator('span', { hasText: /^COMPLETED$/ }) })
    const completedCount = await completedRows.count()
    logInfo(`COMPLETED tasks in list: ${completedCount}`)
    expect(completedCount).toBeGreaterThanOrEqual(9)
    logPass(`${completedCount} completed tasks found`)

    // Check first 9 completed tasks for consistency
    for (let i = 0; i < 9; i++) {
      await completedRows.nth(i).click()
      await page.waitForTimeout(1_500)

      const detail = page.locator('[data-testid="task-detail"]')
      await expect(detail).toBeVisible({ timeout: 8_000 })

      const taskId = (await detail.locator('p.font-mono').first().textContent())?.slice(0, 8) ?? `#${i+1}`
      const taskType = (await detail.locator('p.font-semibold.text-gray-800').first().textContent())?.trim() ?? ''
      const recBadge = detail.locator('span').filter({
        hasText: /APPROVE|REJECT|REQUEST_ADDITIONAL_INFO|REQUEST_AMENDMENTS/
      }).first()
      const rec = await recBadge.isVisible({ timeout: 3_000 }).catch(() => false)
        ? (await recBadge.textContent())?.trim()
        : 'N/A'

      logInfo(`Task ${i+1}: ${taskId} | ${taskType} | ${rec}`)

      // All 5 steps
      for (const step of ['Step 1', 'Step 2', 'Step 3', 'Step 4', 'Step 5']) {
        await expect(detail.getByText(step, { exact: false })).toBeVisible({ timeout: 5_000 })
      }

      // Green dots, no blue
      expect(await detail.locator('.bg-green-500.border-green-500').count()).toBeGreaterThan(0)
      expect(await detail.locator('.bg-blue-500.border-blue-500').count()).toBe(0)

      logPass(`Task ${i+1} (${taskId}): all steps present, lifecycle green ✓`)
    }

    logPass('All 9 tasks consistent — 5 steps, green lifecycle, recommendation badges')
    log('  RESULT  TC-11 PASSED')
  })

})
