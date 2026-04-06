/**
 * Auditex Dashboard — Playwright E2E Tests
 *
 * TC-01  Dashboard loads, form visible, no console errors
 * TC-02  Submit Document Review   → COMPLETED
 * TC-03  Report detail — EU AI Act accordion + Export JSON
 * TC-04  Submit Risk Analysis     → COMPLETED
 * TC-05  Submit Contract Check    → COMPLETED
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
const PG_CONN   = 'postgresql://auditex:auditex_dev_pw@localhost:5432/auditex'

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

// ── API: active task count ────────────────────────────────────────────────────
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

// ── Force-fail stuck tasks via API before each submit ─────────────────────────
// Uses the ops clear SQL — waits max 30s for Celery to finish current task,
// then force-fails anything still stuck before submitting our test task.
async function ensureQueueClear(label: string): Promise<void> {
  logInfo(`${label} — checking queue`)

  // Wait up to 90s for Celery to finish any currently executing task
  const deadline = Date.now() + 90_000
  while (Date.now() < deadline) {
    const active = await getActiveTasks()
    logInfo(`${label} — active: ${active}`)
    if (active === 0) { logInfo('Queue clear'); return }
    // If only EXECUTING (worker is active right now), wait for it to finish
    await new Promise(r => setTimeout(r, 8_000))
  }

  // Queue didn't clear — force-fail stuck tasks via API endpoint
  // We can't run psql from Playwright, but we can hit the API health check
  // and rely on ops.ps1 clear having been run before playwright starts.
  // Log warning and proceed — the test will poll for 200s so has time.
  logInfo(`${label} — queue did not clear in 90s, proceeding (task will wait in queue)`)
}

// ── Reusable: submit + poll to COMPLETED ─────────────────────────────────────
async function submitAndPoll(
  page: Page,
  taskType: 'document_review' | 'risk_analysis' | 'contract_check',
  document: string,
  criteria: string[],
): Promise<void> {

  await ensureQueueClear(`${taskType}`)

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

  // Click the new task row so it's visible in the detail panel while polling
  logStep('Click new task to show in detail panel')
  await page.locator('button.w-full.text-left').first().click()
  logPass('Task detail panel opened')

  logStep(`Poll for COMPLETED — ${taskType}`)
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

      // Scroll task list to keep newest task visible
      await page.locator('button.w-full.text-left').first().scrollIntoViewIfNeeded()
    } catch (e) { logInfo(`poll error: ${e}`) }
  }

  if (finalStatus === 'COMPLETED') {
    logPass(`${taskType} → COMPLETED`)
  } else {
    logFail(`${taskType} ended: ${finalStatus || 'TIMEOUT'}`)
    throw new Error(`${taskType}: expected COMPLETED got ${finalStatus || 'TIMEOUT'}`)
  }
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

  // ── TC-02 : Document Review ────────────────────────────────────────────────
  test('TC-02  Submit Document Review → COMPLETED', async ({ page }) => {
    logSuite('TC-02  Document Review → COMPLETED')
    test.setTimeout(360_000)

    await submitAndPoll(page, 'document_review',
      `Applicant: Jane Doe
Date of Birth: 22/07/1990
Employment: Product Manager at FinTech Ltd 4 years
Annual Salary: 85000 GBP
Loan Amount Requested: 320000 GBP
Loan Purpose: Residential mortgage
Credit Score: 740`,
      ['Completeness', 'Income Verification'],
    )
    log('  RESULT  TC-02 PASSED')
  })

  // ── TC-03 : Report detail ──────────────────────────────────────────────────
  test('TC-03  Task detail shows report and export downloads JSON', async ({ page }) => {
    logSuite('TC-03  Report visible + export downloads JSON')
    test.setTimeout(120_000)

    await page.goto(BASE_URL, { waitUntil: 'networkidle' })
    await page.reload({ waitUntil: 'networkidle' })
    logPass('Page loaded')

    logStep('Find COMPLETED + Report ready task')
    await expect(
      page.locator('button.w-full.text-left')
        .filter({ has: page.locator('span', { hasText: /^COMPLETED$/ }) })
        .filter({ hasText: 'Report ready' }).first()
    ).toBeVisible({ timeout: 30_000 })
    logPass('Found')

    await page.locator('button.w-full.text-left')
      .filter({ has: page.locator('span', { hasText: /^COMPLETED$/ }) })
      .filter({ hasText: 'Report ready' }).first().click()

    await expect(page.locator('p.font-mono').first()).toBeVisible({ timeout: 10_000 })
    logInfo('Task: ' + (await page.locator('p.font-mono').first().textContent())?.trim())

    await expect(page.getByText('Plain English Summary')).toBeVisible({ timeout: 60_000 })
    logPass('Plain English Summary visible')

    await expect(page.getByText('EU AI Act Compliance')).toBeVisible({ timeout: 15_000 })
    logPass('EU AI Act visible')

    const articleBtn = page.locator('button').filter({ hasText: /Article/ }).first()
    await expect(articleBtn).toBeVisible({ timeout: 10_000 })
    logInfo('Article: ' + (await articleBtn.textContent())?.trim().slice(0, 60))
    await articleBtn.click()
    logPass('Article expanded')

    const [download] = await Promise.all([
      page.waitForEvent('download', { timeout: 20_000 }),
      page.getByRole('button', { name: /Export EU AI Act JSON/i }).click(),
    ])
    const filename = download.suggestedFilename()
    expect(filename).toMatch(/^auditex-report-.+\.json$/)
    logPass(`Downloaded: ${filename}`)

    const savePath = path.join(resultsDir, filename)
    await download.saveAs(savePath)
    const parsed = JSON.parse(fs.readFileSync(savePath, 'utf-8'))
    expect(parsed).toHaveProperty('task_id')
    expect(Array.isArray(parsed.articles)).toBe(true)
    logInfo(`articles=${parsed.articles.length}`)
    logPass('JSON valid')

    log('  RESULT  TC-03 PASSED')
  })

  // ── TC-04 : Risk Analysis ──────────────────────────────────────────────────
  test('TC-04  Submit Risk Analysis → COMPLETED', async ({ page }) => {
    logSuite('TC-04  Risk Analysis → COMPLETED')
    test.setTimeout(360_000)

    await submitAndPoll(page, 'risk_analysis',
      `Portfolio: Small business loan application
Business Name: Sunrise Bakery Ltd
Trading Period: 2 years
Annual Revenue: 180000 GBP
Net Profit Margin: 8%
Existing Liabilities: 45000 GBP CBILS loan outstanding
Directors: 2 personal guarantees provided
Sector: Food and Beverage
Requested Facility: 80000 GBP revolving credit
Collateral: Commercial premises valued at 220000 GBP`,
      ['Risk Assessment', 'Completeness'],
    )
    log('  RESULT  TC-04 PASSED')
  })

  // ── TC-05 : Contract Check ─────────────────────────────────────────────────
  test('TC-05  Submit Contract Check → COMPLETED', async ({ page }) => {
    logSuite('TC-05  Contract Check → COMPLETED')
    test.setTimeout(360_000)

    await submitAndPoll(page, 'contract_check',
      `CONTRACT SUMMARY
Parties: DataFlow Analytics Ltd Processor and MedTech Solutions Ltd Controller
Type: Data Processing Agreement
Jurisdiction: England and Wales
Key Terms:
Processor may retain data for 7 years post-contract
No explicit right-to-erasure mechanism specified
Sub-processors: AWS EU-West-2 and Snowflake US-East
Breach notification window: 96 hours
Liability cap: 10000 GBP
GDPR Article 28 compliance: Partial
AI-assisted processing: Yes automated credit scoring module`,
      ['Completeness', 'Risk Assessment'],
    )
    log('  RESULT  TC-05 PASSED')
  })

})
