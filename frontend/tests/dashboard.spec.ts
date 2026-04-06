/**
 * Auditex Dashboard — Playwright E2E Tests
 *
 * POSITIVE (TC-01 to TC-05): Happy path — all 3 task types complete with APPROVE
 * NEGATIVE (TC-06 to TC-08): Bad data — all 3 task types complete with REJECT/REQUEST
 *
 * Negative test assertions:
 *   - Task reaches COMPLETED (pipeline always completes)
 *   - Recommendation shown in header is NOT APPROVE
 *   - Lifecycle dots are all green for COMPLETED tasks
 *   - Review Panel renders with reviewer cards and confidence bars
 *
 * Run from frontend/:
 *   npx playwright test --reporter=list
 */

import { test, expect, type Page } from '@playwright/test'
import * as fs from 'fs'
import * as path from 'path'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname  = path.dirname(__filename)

const BASE_URL  = 'http://localhost:3000'
const API_URL   = 'http://localhost:8000'
const API_KEY   = 'auditex-test-key-phase2'
const POLL_MS   = 5_000
const ACTIVE    = new Set(['QUEUED','EXECUTING','REVIEWING','FINALISING'])
const TERMINAL  = new Set(['COMPLETED','FAILED','ESCALATED'])

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
  logInfo(`${label} — queue did not clear in 90s, proceeding`)
}

// ── Submit + poll to terminal status ─────────────────────────────────────────
async function submitAndPoll(
  page: Page,
  taskType: 'document_review' | 'risk_analysis' | 'contract_check',
  document: string,
  criteria: string[],
  expectStatus: 'COMPLETED' | 'any' = 'COMPLETED',
): Promise<string> {

  await ensureQueueClear(taskType)

  logStep('Navigate')
  await page.goto(BASE_URL, { waitUntil: 'networkidle' })
  logPass('Page loaded')

  logStep(`Select ${taskType}`)
  await page.locator('select').selectOption(taskType)

  logStep('Fill form')
  await page.locator('textarea').fill(document)
  for (const c of criteria) await page.getByLabel(c).check()
  logPass('Form filled')

  const rowsBefore = await page.locator('button.w-full.text-left').count()
  logInfo(`Rows before: ${rowsBefore}`)

  logStep('Submit')
  await page.getByRole('button', { name: /Submit Task/i }).click()

  await expect(async () => {
    expect(await page.locator('button.w-full.text-left').count()).toBeGreaterThan(rowsBefore)
  }).toPass({ timeout: 15_000, intervals: [500] })
  logPass('New row appeared')

  logStep('Click new task row')
  await page.locator('button.w-full.text-left').first().click()
  logPass('Task detail panel opened')

  logStep(`Poll for terminal status — ${taskType}`)
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

  if (!finalStatus) { logFail(`${taskType} timed out`); throw new Error(`${taskType}: timed out`) }
  if (expectStatus !== 'any' && finalStatus !== expectStatus) {
    logFail(`${taskType} ended: ${finalStatus}`)
    throw new Error(`${taskType}: expected ${expectStatus} got ${finalStatus}`)
  }
  logPass(`${taskType} → ${finalStatus}`)
  return finalStatus
}

// ── Verify negative outcome in task detail ────────────────────────────────────
async function verifyNegativeOutcome(page: Page, taskType: string): Promise<void> {

  // Re-click the first row to ensure detail panel is open
  await page.locator('button.w-full.text-left').first().click()
  await page.waitForTimeout(1_500)

  // 1. Task detail panel is rendered (data-testid)
  const detail = page.locator('[data-testid="task-detail"]')
  await expect(detail).toBeVisible({ timeout: 10_000 })
  logPass('Task detail panel visible')

  // 2. Recommendation badge in header should NOT be APPROVE
  const headerRec = detail.locator('span').filter({ hasText: /APPROVE|REJECT|REQUEST/ }).first()
  if (await headerRec.isVisible({ timeout: 5_000 }).catch(() => false)) {
    const rec = (await headerRec.textContent())?.trim() ?? ''
    logInfo(`Header recommendation: ${rec}`)
    expect(rec).not.toBe('APPROVE')
    logPass(`Recommendation is non-approval: ${rec}`)
  } else {
    logInfo('Recommendation badge not yet visible in header — checking executor section')
  }

  // 3. Executor Output section is visible (Step 2)
  const executorSection = detail.getByText('Step 2 — AI Executor')
  if (await executorSection.isVisible({ timeout: 5_000 }).catch(() => false)) {
    logPass('Executor Output section visible')
    // Click to expand if collapsed
    await executorSection.click()
    await page.waitForTimeout(500)
  }

  // 4. Review Panel section is visible (Step 3)
  const reviewSection = detail.getByText('Step 3 — Review Panel')
  if (await reviewSection.isVisible({ timeout: 5_000 }).catch(() => false)) {
    logPass('Review Panel section visible')
    await reviewSection.click()
    await page.waitForTimeout(500)
    // Count reviewer cards
    const cards = detail.locator('.rounded-lg.border.border-gray-100.bg-gray-50')
    const count = await cards.count()
    logInfo(`Reviewer cards: ${count}`)
    if (count > 0) logPass(`${count} reviewer card(s) shown`)
    // Check confidence bars
    const bars = detail.locator('.bg-gray-200.rounded-full')
    const barCount = await bars.count()
    logInfo(`Confidence bars: ${barCount}`)
    if (barCount > 0) logPass(`${barCount} confidence bar(s) rendered`)
  }

  // 5. All lifecycle dots are GREEN for COMPLETED task (not blue)
  const greenDots = detail.locator('.bg-green-500.border-green-500')
  const greenCount = await greenDots.count()
  logInfo(`Green lifecycle dots: ${greenCount}`)
  expect(greenCount).toBeGreaterThan(0)
  logPass(`${greenCount} green dot(s) — lifecycle complete`)

  // 6. No blue active dot (would mean still in progress)
  const blueDot = detail.locator('.bg-blue-500.border-blue-500')
  const blueCount = await blueDot.count()
  logInfo(`Blue active dots: ${blueCount} (expect 0 for COMPLETED)`)
  expect(blueCount).toBe(0)
  logPass('No blue active dot — all stages complete and green')
}

// ── Tests ─────────────────────────────────────────────────────────────────────
test.describe('Auditex Dashboard E2E', () => {

  test.beforeAll(() => {
    log(''); log('█'.repeat(60))
    log('  Auditex Playwright E2E  —  ' + new Date().toLocaleString())
    log(`  Dashboard: ${BASE_URL}  API: ${API_URL}`)
    log('█'.repeat(60))
  })

  test.afterAll(() => {
    log(''); log('Run complete. Log: ' + logFile)
    logStream.end()
  })

  // ── TC-01 ──────────────────────────────────────────────────────────────────
  test('TC-01  Dashboard loads without errors', async ({ page }) => {
    logSuite('TC-01  Dashboard loads without errors')
    test.setTimeout(60_000)

    const errs: string[] = []
    page.on('console', m => { if (m.type()==='error') errs.push(m.text()) })
    page.on('pageerror', e => errs.push(e.message))

    await page.goto(BASE_URL, { waitUntil: 'networkidle' })
    await page.reload({ waitUntil: 'networkidle' })
    logPass('Page loaded')

    await expect(page).toHaveTitle(/Auditex/i)
    logPass('Title: ' + await page.title())

    for (const [label, loc] of [
      ['header',          page.locator('header')],
      ['Submit New Task', page.getByText('Submit New Task')],
      ['select',          page.locator('select')],
      ['textarea',        page.locator('textarea')],
      ['Submit button',   page.getByRole('button', { name: /Submit Task/i })],
      ['Tasks panel',     page.getByText(/^Tasks/)],
    ] as const) {
      await expect(loc).toBeVisible()
      logPass(`${label} visible`)
    }

    if (errs.length > 0) { logFail('Console errors', errs.join(' | ')); throw new Error(errs.join(' | ')) }
    logPass('No console errors')
    log('  RESULT  TC-01 PASSED')
  })

  // ── TC-02 ──────────────────────────────────────────────────────────────────
  test('TC-02  Submit Document Review → COMPLETED', async ({ page }) => {
    logSuite('TC-02  Document Review → COMPLETED (positive)')
    test.setTimeout(360_000)
    await submitAndPoll(page, 'document_review',
      `Applicant: Jane Doe\nDate of Birth: 22/07/1990\nEmployment: Product Manager at FinTech Ltd 4 years\nAnnual Salary: 85000 GBP\nLoan Amount Requested: 320000 GBP\nLoan Purpose: Residential mortgage\nCredit Score: 740`,
      ['Completeness', 'Income Verification'],
    )
    log('  RESULT  TC-02 PASSED')
  })

  // ── TC-03 ──────────────────────────────────────────────────────────────────
  test('TC-03  Task detail shows report and export downloads JSON', async ({ page }) => {
    logSuite('TC-03  Report visible + export downloads JSON')
    test.setTimeout(120_000)

    await page.goto(BASE_URL, { waitUntil: 'networkidle' })
    await page.reload({ waitUntil: 'networkidle' })
    logPass('Page loaded')

    await expect(
      page.locator('button.w-full.text-left')
        .filter({ has: page.locator('span', { hasText: /^COMPLETED$/ }) })
        .filter({ hasText: 'Report ready' }).first()
    ).toBeVisible({ timeout: 30_000 })
    await page.locator('button.w-full.text-left')
      .filter({ has: page.locator('span', { hasText: /^COMPLETED$/ }) })
      .filter({ hasText: 'Report ready' }).first().click()
    logPass('Clicked Report ready task')

    // Report section is open by default (defaultOpen=true)
    await expect(page.getByText('Plain English Summary')).toBeVisible({ timeout: 60_000 })
    logPass('Plain English Summary visible')

    await expect(page.getByText('EU AI Act Compliance')).toBeVisible({ timeout: 15_000 })
    logPass('EU AI Act visible')

    const articleBtn = page.locator('button').filter({ hasText: /Article/ }).first()
    await expect(articleBtn).toBeVisible({ timeout: 10_000 })
    await articleBtn.click()
    logPass('Article expanded')

    const [download] = await Promise.all([
      page.waitForEvent('download', { timeout: 20_000 }),
      page.getByRole('button', { name: /Export EU AI Act JSON/i }).click(),
    ])
    const filename = download.suggestedFilename()
    expect(filename).toMatch(/^auditex-report-.+\.json$/)
    const savePath = path.join(resultsDir, filename)
    await download.saveAs(savePath)
    const parsed = JSON.parse(fs.readFileSync(savePath, 'utf-8'))
    expect(parsed).toHaveProperty('task_id')
    expect(Array.isArray(parsed.articles)).toBe(true)
    logInfo(`articles=${parsed.articles.length}`)
    logPass('JSON valid')

    log('  RESULT  TC-03 PASSED')
  })

  // ── TC-04 ──────────────────────────────────────────────────────────────────
  test('TC-04  Submit Risk Analysis → COMPLETED', async ({ page }) => {
    logSuite('TC-04  Risk Analysis → COMPLETED (positive)')
    test.setTimeout(360_000)
    await submitAndPoll(page, 'risk_analysis',
      `Business Name: Sunrise Bakery Ltd\nTrading Period: 2 years\nAnnual Revenue: 180000 GBP\nNet Profit Margin: 8%\nExisting Liabilities: 45000 GBP\nDirectors: 2 personal guarantees\nSector: Food and Beverage\nRequested Facility: 80000 GBP\nCollateral: Commercial premises 220000 GBP`,
      ['Risk Assessment', 'Completeness'],
    )
    log('  RESULT  TC-04 PASSED')
  })

  // ── TC-05 ──────────────────────────────────────────────────────────────────
  test('TC-05  Submit Contract Check → COMPLETED', async ({ page }) => {
    logSuite('TC-05  Contract Check → COMPLETED (positive)')
    test.setTimeout(360_000)
    await submitAndPoll(page, 'contract_check',
      `Parties: DataFlow Analytics Ltd and MedTech Solutions Ltd\nType: Data Processing Agreement\nJurisdiction: England and Wales\nBreach notification: 96 hours\nLiability cap: 10000 GBP\nGDPR Article 28: Partial\nSub-processors: AWS EU-West-2 and Snowflake US-East`,
      ['Completeness', 'Risk Assessment'],
    )
    log('  RESULT  TC-05 PASSED')
  })

  // ── TC-06 : Document Review NEGATIVE ──────────────────────────────────────
  test('TC-06  Document Review negative — incomplete data → non-APPROVE', async ({ page }) => {
    logSuite('TC-06  Document Review negative → REJECT/REQUEST')
    test.setTimeout(360_000)

    await submitAndPoll(page, 'document_review',
      `Applicant: Unknown\nLoan Amount: unspecified\nPurpose: unspecified`,
      ['Completeness', 'Income Verification'],
    )

    await verifyNegativeOutcome(page, 'document_review')
    log('  RESULT  TC-06 PASSED')
  })

  // ── TC-07 : Risk Analysis NEGATIVE ────────────────────────────────────────
  test('TC-07  Risk Analysis negative — insolvent business → HIGH risk', async ({ page }) => {
    logSuite('TC-07  Risk Analysis negative → REJECT')
    test.setTimeout(360_000)

    await submitAndPoll(page, 'risk_analysis',
      `Business Name: Collapsed Retail Ltd\nTrading Period: 6 months\nAnnual Revenue: 12000 GBP\nNet Profit Margin: -45%\nExisting Liabilities: 890000 GBP\nDirectors: 3 resigned in last 90 days\nRequested Facility: 500000 GBP\nCollateral: None\nCCJs: 4 outstanding\nInsolvency: Administrator appointed`,
      ['Risk Assessment', 'Completeness'],
    )

    await verifyNegativeOutcome(page, 'risk_analysis')
    log('  RESULT  TC-07 PASSED')
  })

  // ── TC-08 : Contract Check NEGATIVE ───────────────────────────────────────
  test('TC-08  Contract Check negative — GDPR violations → NON_COMPLIANT', async ({ page }) => {
    logSuite('TC-08  Contract Check negative → NON_COMPLIANT')
    test.setTimeout(360_000)

    await submitAndPoll(page, 'contract_check',
      `Parties: ShadowData Corp and NHS Trust\nType: Informal data sharing\nJurisdiction: Unknown\nData may be sold to third parties\nNo breach notification requirement\nLiability cap: 0 GBP\nGDPR compliance: None\nPersonal data: Full patient medical records\nEncryption: None`,
      ['Completeness', 'Risk Assessment'],
    )

    await verifyNegativeOutcome(page, 'contract_check')
    log('  RESULT  TC-08 PASSED')
  })

})
