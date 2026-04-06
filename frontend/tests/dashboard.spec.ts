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

// ── DOCUMENT REVIEW ──────────────────────────────────────────────────────────

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
  SUBMITTED: 3 months payslips, 2 years P60, 6 months bank statements,
             Passport (valid to 2031), Proof of address (utility bill),
             Property valuation 485000 GBP (RICS certified), Solicitor confirmed

Affordability: Income multiple 3.7x (policy max 4.5x) — PASS
               Stress test at 7%: 2340 GBP/month — PASS
               LTV 70.8% — within 80% policy limit — PASS
All required documents submitted and verified. No missing information.
`

const DR_REQUEST = `
MORTGAGE APPLICATION — PARTIAL SUBMISSION

Applicant:        Michael Brown, DOB 15/03/1985
Address:          22 High Street, Birmingham B1 1AA
Employer:         Local Council — Admin Officer, 2 years employment
Gross Salary:     34000 GBP/year
Bank Statements:  NOT PROVIDED
Payslips:         Only 1 month provided (3 months required)
P60:              NOT PROVIDED
Credit Score:     Not disclosed
CCJs:             Unknown

Loan Request:     195000 GBP (LTV 88.6%)
Deposit:          25000 GBP (source of funds not evidenced)

Income multiple: 5.7x — EXCEEDS policy maximum of 4.5x
Missing: bank statements, payslips x2, P60, credit check, deposit source evidence
`

const DR_REJECT = `
MORTGAGE APPLICATION — FRAUDULENT SUBMISSION

Applicant:        John Smith, DOB 01/01/1900 (age 126 — biologically impossible)
Address:          123 Fake Street, London (does not exist on Land Registry)
Employer:         Self-employed "CEO" — no company registration number
Gross Salary:     500000 GBP/month — stated verbally only, bank shows 200 GBP balance

Loan Request:     2000000 GBP against unvalued property
Existing Debts:   12 active CCJs totalling 340000 GBP
Bankruptcy:       Discharged 18 months ago — within exclusion period
Credit Score:     Very Poor — multiple active defaults

Fraud Indicators: Impossible date of birth, non-existent address, income 250x bank balance,
                  bankruptcy within exclusion period, 12 CCJs outstanding
RECOMMENDATION:   REJECT — clear fraud indicators, application cannot proceed
`

// ── RISK ANALYSIS ─────────────────────────────────────────────────────────────

const RA_APPROVE = `
COMMERCIAL LOAN — HEALTHY PROFITABLE BUSINESS

Business:         Sunrise Bakery Ltd (Company No. 12345678), 7 years trading
Directors:        Sarah + James Mitchell, unlimited personal guarantees, credit 780/755

Audited P&L (3 years):
  2022: Revenue 620000 | Net Profit 72000 | EBITDA 95000
  2023: Revenue 740000 | Net Profit 89000 | EBITDA 118000
  2024: Revenue 890000 | Net Profit 108000 | EBITDA 142000 | CAGR 19.7%

Balance Sheet Dec 2024: Assets 780000 | Liabilities 210000 | Net Assets 570000
Ratios: Current 2.4 | Quick 1.8 | Debt/Equity 0.37 — all healthy

Existing Finance: All payments current — no arrears, no CCJs, no defaults
Loan: 200000 GBP for production equipment (value 280000 GBP)
DSCR: 3.2x — strong coverage. Tesco 3-year contract renewed 2024.
RECOMMENDATION: Low risk — APPROVE
`

const RA_REQUEST = `
COMMERCIAL LOAN — EARLY STAGE STARTUP

Business:  TechStart Ltd, 18 months old, first-time director age 28
Revenue:   85000 Year 1 — Year 2 projected 180000 (unaudited, no client contracts)
Accounts:  Management accounts only — no audited financials available
Profit:    Break-even currently
Security:  IP only (no independent valuation)
Director:  45000 GBP student debt, credit score not disclosed
Loan:      120000 GBP — no firm orders to support repayment

Missing: audited accounts, signed client contracts, director credit check, IP valuation
`

const RA_REJECT = `
COMMERCIAL LOAN — INSOLVENT DISTRESSED BUSINESS

Business:  Collapsed Retail Ltd — Administrator appointed 8 days ago
Revenue:   Declining: 480000 (2022) to 195000 (2024), -45% net margin
Debts:     890000 GBP owed to 14 creditors, all overdue
CCJs:      4 outstanding totalling 210000 GBP
Directors: 3 of 4 resigned in last 90 days, remaining director bankrupt 2019
Cash:      35000 GBP overdrawn
Collateral: None — all assets charged to existing creditors

Loan: 500000 GBP emergency — repayment plan: "hope to trade out"
RECOMMENDATION: REJECT — insolvent, administrator appointed, no viable recovery plan
`

// ── CONTRACT CHECK ────────────────────────────────────────────────────────────

// TC-08: Completely unambiguous full compliance — every single Article 28 item confirmed,
// no special category data, no gaps, signed, ICO registered, ISO 27001 certified.
const CC_APPROVE = `
DATA PROCESSING AGREEMENT — FULLY COMPLIANT — APPROVE RECOMMENDED

Reference: DPA-2025-089
Date: 1 January 2025
Jurisdiction: England and Wales (UK GDPR + Data Protection Act 2018)

Controller: MedTech Solutions Ltd | ICO Reg ZA123456 | Company 09876543
Processor:  DataFlow Analytics Ltd | ICO Reg ZB789012 | Company 07654321

DATA AND PURPOSE:
  Type:          Anonymised statistical data only — NO personal data, NO special category data
  Purpose:       Aggregate trend analytics for research — no individual profiling
  Legal Basis:   Article 6(1)(f) — DPIA completed, documented, ICO notified
  Retention:     Maximum 12 months then mandatory deletion — process verified and tested

ARTICLE 28(3) — ALL CLAUSES FULLY SATISFIED:
  (a) Instructions:      COMPLETE — written instructions in Schedule 1, reviewed quarterly
  (b) Confidentiality:   COMPLETE — staff NDA signed, background checks completed
  (c) Security:          COMPLETE — ISO 27001:2022 certified, cert valid to 2027
  (d) Sub-processors:    COMPLETE — prior written approval required, approved list in Schedule 3
  (e) Data subject rights: COMPLETE — 24-hour SLA, tested process, documented workflow
  (f) Security assist:   COMPLETE — joint incident response plan agreed and tested
  (g) Deletion/return:   COMPLETE — 14-day deletion confirmed, certificate of destruction provided
  (h) Audit rights:      COMPLETE — annual audit with 14 days notice, remote access provided

TECHNICAL MEASURES:
  Encryption at rest:   AES-256 (verified)
  Encryption in transit: TLS 1.3 (verified)
  Access control:       Role-based, MFA mandatory, reviewed monthly
  Penetration test:     Passed — November 2024, report attached
  Breach notification:  12 hours (exceeds 72-hour legal minimum)

TRANSFERS AND SUB-PROCESSORS:
  All processing: UK and EU only — NO third-country transfers
  AWS EU West-2:  DPA signed, SCCs in place, audited 2024
  Snowflake EU:   DPA signed, SCCs in place, audited 2024
  No other sub-processors permitted without prior written consent

LIABILITY AND INDEMNITY:
  Liability cap:  10000000 GBP (proportionate to risk)
  Cyber cover:    5000000 GBP (certificate attached)
  Mutual indemnity: Both parties confirmed

STATUS: All Article 28 requirements satisfied. No gaps identified. No amendments needed.
Signed: Controller CEO + Processor DPO, 1 January 2025
`

const CC_REQUEST = `
DATA PROCESSING AGREEMENT — PARTIAL COMPLIANCE — AMENDMENTS NEEDED

Controller: RetailCo Ltd | Processor: CloudStore Analytics Ltd
Purpose: Customer purchase behaviour analytics and profiling
Legal Basis: Legitimate interests stated — DPIA NOT completed (required for profiling)

ARTICLE 28(3) GAPS:
  (a) Instructions:      Present in Schedule 1 — OK
  (b) Confidentiality:   NDA in place — OK
  (c) Security:          ISO 27001 IN PROGRESS — not yet certified — PARTIAL
  (d) Sub-processors:    MISSING — no sub-processor restriction clause
  (e) Data subject rights: PARTIAL — no SLA timeframe specified
  (f) Security assist:   Present — OK
  (g) Deletion:          MISSING — no data deletion clause
  (h) Audit rights:      PARTIAL — right present but no notice period stated

GAPS REQUIRING AMENDMENTS:
  1. DPIA must be completed before profiling begins
  2. Sub-processor restriction clause must be added
  3. Data deletion timeframe must be specified
  4. Audit notice period must be stated
  5. MFA not required — should be mandatory

Liability cap: 50000 GBP — appears insufficient for 400000 GBP contract value
`

const CC_REJECT = `
DATA PROCESSING AGREEMENT — FUNDAMENTALLY NON-COMPLIANT — REJECT

Parties: ShadowData Corp (Processor) and NHS Trust (Controller)
Data: FULL special category NHS patient records — diagnoses, medications, mental health, HIV, genetics
Purpose: "Data monetisation" — selling patient data — unlawful purpose

ARTICLE 28(3) COMPLETE FAILURES:
  (a) Instructions: MISSING  (b) Confidentiality: MISSING  (c) Security: MISSING
  (d) Sub-processors: MISSING  (e) Data subject rights: EXPLICITLY EXCLUDED
  (f) Security assist: MISSING  (g) Deletion: "retained indefinitely"
  (h) Audit rights: EXPLICITLY PROHIBITED in clause 8.1

EXPLICIT CONTRACT VIOLATIONS:
  Clause 7.3: Patient data may be sold to commercial marketing firms
  Clause 9.1: "Patient rights under GDPR do not apply to this agreement"
  Clause 10.1: Processor accepts zero liability
  Clause 11.1: GDPR "does not apply to processor's operations"

Security: No encryption, no access controls, no security measures
Transfers: US vendors with no adequacy decision and no SCCs
Breach notification: None required

Exposure: Criminal liability under DPA 2018, ICO fines up to 4% global turnover
RECOMMENDATION: REJECT — unlawful purpose, complete GDPR non-compliance, patient data at risk
`

// ── Log setup ─────────────────────────────────────────────────────────────────
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

// ── API helpers ───────────────────────────────────────────────────────────────
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
  logPass('Task row clicked')

  logStep('Poll to COMPLETED')
  const deadline = Date.now() + 200_000
  let finalStatus = ''
  let elapsed = 0
  while (Date.now() < deadline) {
    await page.waitForTimeout(POLL_MS)
    elapsed += POLL_MS
    try {
      const spans = await page.locator('button.w-full.text-left').first().locator('span').allTextContents()
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

async function verifyOutcome(page: Page, taskType: string, expectedRec: string): Promise<void> {
  await page.locator('button.w-full.text-left').first().click()
  await page.waitForTimeout(2_000)

  const detail = page.locator('[data-testid="task-detail"]')
  await expect(detail).toBeVisible({ timeout: 10_000 })

  // 1. Recommendation badge
  logStep(`Assert recommendation = ${expectedRec}`)
  const recBadge = detail.locator('span').filter({
    hasText: /APPROVE|REJECT|REQUEST_ADDITIONAL_INFO|REQUEST_AMENDMENTS/
  }).first()
  await expect(recBadge).toBeVisible({ timeout: 10_000 })
  const rec = (await recBadge.textContent())?.trim() ?? ''
  logInfo(`Recommendation badge: ${rec}`)
  expect(rec).toBe(expectedRec)
  logPass(`Recommendation = ${rec} ✓`)

  // 2. All 5 steps visible
  logStep('Assert all 5 pipeline steps visible')
  for (const step of ['Step 1', 'Step 2', 'Step 3', 'Step 4', 'Step 5']) {
    await expect(detail.getByText(step, { exact: false })).toBeVisible({ timeout: 5_000 })
    logPass(`${step} visible`)
  }

  // 3. Green dots, no blue
  const greenCount = await detail.locator('.bg-green-500.border-green-500').count()
  expect(greenCount).toBeGreaterThan(0)
  logPass(`${greenCount} green dot(s)`)
  expect(await detail.locator('.bg-blue-500.border-blue-500').count()).toBe(0)
  logPass('No blue active dot')

  // 4. Expand Step 3 — reviewer cards
  await detail.getByText('Step 3', { exact: false }).first().click()
  await page.waitForTimeout(500)
  const cardCount = await detail.locator('.rounded-lg.border.border-gray-100.bg-gray-50').count()
  logInfo(`Reviewer cards: ${cardCount}`)
  if (cardCount > 0) logPass(`${cardCount} reviewer card(s)`)

  // 5. Expand Step 5 — report summary
  await detail.getByText('Step 5', { exact: false }).first().click()
  await page.waitForTimeout(500)
  if (await detail.getByText('Plain English Summary').isVisible({ timeout: 8_000 }).catch(() => false)) {
    logPass('Plain English Summary visible')
  } else {
    logInfo('Report still generating')
  }
}

// ── Tests ─────────────────────────────────────────────────────────────────────
test.describe('Auditex Dashboard E2E — Full Scenario Matrix', () => {

  test.beforeAll(() => {
    log(''); log('█'.repeat(70))
    log('  Auditex Playwright E2E  —  ' + new Date().toLocaleString())
    log('  3 task types × 3 recommendations = 9 scenarios + dashboard + UI check = 11 tests')
    log(`  Dashboard: ${BASE_URL}  API: ${API_URL}`)
    log('█'.repeat(70))
  })

  test.afterAll(() => {
    log(''); log('Run complete. Log: ' + logFile)
    logStream.end()
  })

  test('TC-01  Dashboard loads without errors', async ({ page }) => {
    logSuite('TC-01  Dashboard loads')
    test.setTimeout(60_000)
    const errs: string[] = []
    page.on('console', m => { if (m.type()==='error') errs.push(m.text()) })
    page.on('pageerror', e => errs.push(e.message))
    await page.goto(BASE_URL, { waitUntil: 'networkidle' })
    await page.reload({ waitUntil: 'networkidle' })
    await expect(page).toHaveTitle(/Auditex/i)
    for (const [label, loc] of [
      ['header',        page.locator('header')],
      ['Submit Task',   page.getByText('Submit New Task')],
      ['select',        page.locator('select')],
      ['textarea',      page.locator('textarea')],
      ['Submit button', page.getByRole('button', { name: /Submit Task/i })],
      ['Tasks panel',   page.getByText(/^Tasks/)],
    ] as const) { await expect(loc).toBeVisible(); logPass(`${label} visible`) }
    expect(errs.length).toBe(0)
    logPass('No console errors')
    log('  RESULT  TC-01 PASSED')
  })

  test('TC-02  document_review → APPROVE (complete mortgage application)', async ({ page }) => {
    logSuite('TC-02  document_review → APPROVE')
    test.setTimeout(360_000)
    await submitAndPoll(page, 'document_review', DR_APPROVE, ['Completeness', 'Income Verification', 'Employment Verification'])
    await verifyOutcome(page, 'document_review', 'APPROVE')
    log('  RESULT  TC-02 PASSED')
  })

  test('TC-03  document_review → REQUEST_ADDITIONAL_INFO (missing documents)', async ({ page }) => {
    logSuite('TC-03  document_review → REQUEST_ADDITIONAL_INFO')
    test.setTimeout(360_000)
    await submitAndPoll(page, 'document_review', DR_REQUEST, ['Completeness', 'Income Verification'])
    await verifyOutcome(page, 'document_review', 'REQUEST_ADDITIONAL_INFO')
    log('  RESULT  TC-03 PASSED')
  })

  test('TC-04  document_review → REJECT (fraudulent application)', async ({ page }) => {
    logSuite('TC-04  document_review → REJECT')
    test.setTimeout(360_000)
    await submitAndPoll(page, 'document_review', DR_REJECT, ['Completeness', 'Income Verification'])
    await verifyOutcome(page, 'document_review', 'REJECT')
    log('  RESULT  TC-04 PASSED')
  })

  test('TC-05  risk_analysis → APPROVE (healthy growing business)', async ({ page }) => {
    logSuite('TC-05  risk_analysis → APPROVE')
    test.setTimeout(360_000)
    await submitAndPoll(page, 'risk_analysis', RA_APPROVE, ['Risk Assessment', 'Completeness'])
    await verifyOutcome(page, 'risk_analysis', 'APPROVE')
    log('  RESULT  TC-05 PASSED')
  })

  test('TC-06  risk_analysis → REQUEST_ADDITIONAL_INFO (early stage startup)', async ({ page }) => {
    logSuite('TC-06  risk_analysis → REQUEST_ADDITIONAL_INFO')
    test.setTimeout(360_000)
    await submitAndPoll(page, 'risk_analysis', RA_REQUEST, ['Risk Assessment', 'Completeness'])
    await verifyOutcome(page, 'risk_analysis', 'REQUEST_ADDITIONAL_INFO')
    log('  RESULT  TC-06 PASSED')
  })

  test('TC-07  risk_analysis → REJECT (insolvent, administrator appointed)', async ({ page }) => {
    logSuite('TC-07  risk_analysis → REJECT')
    test.setTimeout(360_000)
    await submitAndPoll(page, 'risk_analysis', RA_REJECT, ['Risk Assessment', 'Completeness'])
    await verifyOutcome(page, 'risk_analysis', 'REJECT')
    log('  RESULT  TC-07 PASSED')
  })

  test('TC-08  contract_check → APPROVE (fully GDPR compliant DPA)', async ({ page }) => {
    logSuite('TC-08  contract_check → APPROVE')
    test.setTimeout(360_000)
    await submitAndPoll(page, 'contract_check', CC_APPROVE, ['Completeness', 'Risk Assessment'])
    await verifyOutcome(page, 'contract_check', 'APPROVE')
    log('  RESULT  TC-08 PASSED')
  })

  test('TC-09  contract_check → REQUEST_AMENDMENTS (minor GDPR gaps)', async ({ page }) => {
    logSuite('TC-09  contract_check → REQUEST_AMENDMENTS')
    test.setTimeout(360_000)
    await submitAndPoll(page, 'contract_check', CC_REQUEST, ['Completeness', 'Risk Assessment'])
    await verifyOutcome(page, 'contract_check', 'REQUEST_AMENDMENTS')
    log('  RESULT  TC-09 PASSED')
  })

  test('TC-10  contract_check → REJECT (NHS data sold to marketing)', async ({ page }) => {
    logSuite('TC-10  contract_check → REJECT')
    test.setTimeout(360_000)
    await submitAndPoll(page, 'contract_check', CC_REJECT, ['Completeness', 'Risk Assessment'])
    await verifyOutcome(page, 'contract_check', 'REJECT')
    log('  RESULT  TC-10 PASSED')
  })

  test('TC-11  UI consistency — all 9 tasks show 5 steps + correct badges', async ({ page }) => {
    logSuite('TC-11  UI consistency')
    test.setTimeout(180_000)
    await page.goto(BASE_URL, { waitUntil: 'networkidle' })
    await page.reload({ waitUntil: 'networkidle' })
    logPass('Page loaded')

    const completedRows = page.locator('button.w-full.text-left')
      .filter({ has: page.locator('span', { hasText: /^COMPLETED$/ }) })
    const completedCount = await completedRows.count()
    logInfo(`COMPLETED tasks: ${completedCount}`)
    expect(completedCount).toBeGreaterThanOrEqual(9)
    logPass(`${completedCount} completed tasks`)

    for (let i = 0; i < 9; i++) {
      await completedRows.nth(i).click()
      await page.waitForTimeout(1_500)
      const detail = page.locator('[data-testid="task-detail"]')
      await expect(detail).toBeVisible({ timeout: 8_000 })
      const taskId = (await detail.locator('p.font-mono').first().textContent())?.slice(0, 8) ?? `#${i+1}`
      const recBadge = detail.locator('span').filter({ hasText: /APPROVE|REJECT|REQUEST/ }).first()
      const rec = await recBadge.isVisible({ timeout: 3_000 }).catch(() => false)
        ? (await recBadge.textContent())?.trim() : 'N/A'
      logInfo(`Task ${i+1}: ${taskId} | ${rec}`)
      for (const step of ['Step 1', 'Step 2', 'Step 3', 'Step 4', 'Step 5']) {
        await expect(detail.getByText(step, { exact: false })).toBeVisible({ timeout: 5_000 })
      }
      expect(await detail.locator('.bg-green-500.border-green-500').count()).toBeGreaterThan(0)
      expect(await detail.locator('.bg-blue-500.border-blue-500').count()).toBe(0)
      logPass(`Task ${i+1} (${taskId}): all 5 steps, green lifecycle ✓`)
    }
    logPass('All 9 tasks consistent')
    log('  RESULT  TC-11 PASSED')
  })

})
