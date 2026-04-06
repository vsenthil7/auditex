/**
 * Auditex Dashboard — Playwright E2E Tests
 *
 * TC-01  Dashboard loads, form visible, no console errors
 * TC-02  Submit Document Review → appears → polls to COMPLETED
 * TC-03  Task detail shows report, EU AI Act accordion, Export downloads JSON
 *
 * SEQUENCE:
 *   1. TC-01 runs immediately (UI checks only, ~10s)
 *   2. TC-02 checks API for active tasks before submitting.
 *      If queue is busy it waits up to 3 min for it to clear, THEN submits.
 *      This prevents the "stuck at QUEUED for 5 min" problem.
 *   3. TC-03 clicks a task that has "Report ready" badge (report_available=true)
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

// ── API helper: get active task count directly ────────────────────────────────
async function getActiveTasks(): Promise<number> {
  const res = await fetch(`${API_URL}/api/v1/tasks?page=1&page_size=100`, {
    headers: { 'X-API-Key': API_KEY }
  })
  if (!res.ok) return 0
  const data = await res.json()
  const tasks: any[] = data.tasks ?? []
  return tasks.filter(t => ACTIVE.has(t.status)).length
}

// ── Wait for queue to clear before submitting ─────────────────────────────────
async function waitForQueueClear(label: string, timeoutMs = 180_000): Promise<void> {
  const deadline = Date.now() + timeoutMs
  let waited = 0
  while (Date.now() < deadline) {
    const active = await getActiveTasks()
    logInfo(`${label} — active tasks in queue: ${active}`)
    if (active === 0) { logInfo('Queue clear — ready to submit'); return }
    await new Promise(r => setTimeout(r, 8_000))
    waited += 8_000
  }
  logInfo('Queue did not clear within timeout — proceeding anyway')
}

// ── Tests ─────────────────────────────────────────────────────────────────────
test.describe('Auditex Dashboard E2E', () => {

  test.beforeAll(() => {
    log(''); log('█'.repeat(60))
    log('  Auditex Playwright E2E  —  ' + new Date().toLocaleString())
    log(`  Dashboard: ${BASE_URL}`)
    log(`  API:       ${API_URL}`)
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

    logStep('Navigate + hard reload')
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
  test('TC-02  Submit Document Review task and poll to COMPLETED', async ({ page }) => {
    logSuite('TC-02  Submit → poll to COMPLETED')
    test.setTimeout(360_000)  // 6 min total

    // ── Step 0: Check queue via API before even opening browser ──
    logStep('Check API queue depth before submitting')
    const activeBefore = await getActiveTasks()
    logInfo(`Active tasks in pipeline right now: ${activeBefore}`)
    if (activeBefore > 0) {
      logInfo(`Queue has ${activeBefore} active task(s) — waiting for them to finish first`)
      logInfo('This prevents our new task from waiting behind existing ones')
      await waitForQueueClear('Pre-submit queue check', 180_000)
    } else {
      logInfo('Queue is clear — submitting immediately')
    }

    logStep('Navigate to dashboard')
    await page.goto(BASE_URL, { waitUntil: 'networkidle' })
    await page.reload({ waitUntil: 'networkidle' })
    logPass('Page loaded')

    logStep('Select document_review')
    await page.locator('select').selectOption('document_review')

    const doc = `Applicant: Jane Doe
Date of Birth: 22/07/1990
Employment: Product Manager at FinTech Ltd 4 years
Annual Salary: 85000 GBP
Loan Amount Requested: 320000 GBP
Loan Purpose: Residential mortgage
Credit Score: 740`

    await page.locator('textarea').fill(doc)
    await page.getByLabel('Completeness').check()
    await page.getByLabel('Income Verification').check()
    logPass('Form filled')

    const rowsBefore = await page.locator('button.w-full.text-left').count()
    logInfo(`Task rows before submit: ${rowsBefore}`)

    logStep('Submit task')
    await page.getByRole('button', { name: /Submit Task/i }).click()
    logPass('Submit clicked')

    await expect(async () => {
      expect(await page.locator('button.w-full.text-left').count()).toBeGreaterThan(rowsBefore)
    }).toPass({ timeout: 15_000, intervals: [500] })
    logPass('New row appeared in list')

    logStep('Poll for COMPLETED (queue clear so should take ~60-90s)...')
    const deadline = Date.now() + 200_000
    let finalStatus = ''
    let elapsed = 0

    while (Date.now() < deadline) {
      await page.waitForTimeout(POLL_MS)
      elapsed += POLL_MS
      try {
        const spans   = await page.locator('button.w-full.text-left').first().locator('span').allTextContents()
        const cleaned = spans.map(s => s.trim()).filter(Boolean)
        logInfo(`[${Math.round(elapsed/1000)}s] ${cleaned.join(' | ')}`)
        const term = cleaned.find(s => TERMINAL.has(s))
        if (term) { finalStatus = term; break }
      } catch (e) { logInfo(`poll error: ${e}`) }
    }

    if (finalStatus === 'COMPLETED') {
      logPass('Task reached COMPLETED')
      log('  RESULT  TC-02 PASSED')
    } else {
      logFail(`Ended with: ${finalStatus || 'TIMEOUT'}`)
      throw new Error(`TC-02: expected COMPLETED got ${finalStatus || 'TIMEOUT'}`)
    }
  })

  // ── TC-03 ──────────────────────────────────────────────────────────────────
  test('TC-03  Task detail shows report and export downloads JSON', async ({ page }) => {
    logSuite('TC-03  Report visible + export downloads JSON')
    test.setTimeout(120_000)

    logStep('Navigate')
    await page.goto(BASE_URL, { waitUntil: 'networkidle' })
    await page.reload({ waitUntil: 'networkidle' })
    logPass('Page loaded')

    // Target only tasks with "Report ready" badge — means report_available=true
    logStep('Find COMPLETED task with Report ready badge')
    const reportReadyRow = page.locator('button.w-full.text-left')
      .filter({ has: page.locator('span', { hasText: /^COMPLETED$/ }) })
      .filter({ hasText: 'Report ready' })
      .first()

    await expect(reportReadyRow).toBeVisible({ timeout: 30_000 })
    logPass('Found COMPLETED + Report ready task')

    await reportReadyRow.click()
    logPass('Clicked row')

    logStep('Wait for TaskDetail panel')
    await expect(page.locator('p.font-mono').first()).toBeVisible({ timeout: 10_000 })
    logInfo('Task: ' + (await page.locator('p.font-mono').first().textContent())?.trim())

    logStep('Wait for Plain English Summary (60s)')
    await expect(page.getByText('Plain English Summary')).toBeVisible({ timeout: 60_000 })
    logPass('Plain English Summary visible')

    logStep('Wait for EU AI Act Compliance (15s)')
    await expect(page.getByText('EU AI Act Compliance')).toBeVisible({ timeout: 15_000 })
    logPass('EU AI Act section visible')

    logStep('Expand first article')
    const articleBtn = page.locator('button').filter({ hasText: /Article/ }).first()
    await expect(articleBtn).toBeVisible({ timeout: 10_000 })
    logInfo('Article: ' + (await articleBtn.textContent())?.trim().slice(0, 60))
    await articleBtn.click()
    logPass('Article expanded')

    logStep('Export EU AI Act JSON')
    const [download] = await Promise.all([
      page.waitForEvent('download', { timeout: 20_000 }),
      page.getByRole('button', { name: /Export EU AI Act JSON/i }).click(),
    ])
    const filename = download.suggestedFilename()
    logInfo(`Downloaded: ${filename}`)
    expect(filename).toMatch(/^auditex-report-.+\.json$/)
    logPass(`Filename: ${filename}`)

    const savePath = path.join(resultsDir, filename)
    await download.saveAs(savePath)
    const parsed = JSON.parse(fs.readFileSync(savePath, 'utf-8'))
    expect(parsed).toHaveProperty('task_id')
    expect(Array.isArray(parsed.articles)).toBe(true)
    logInfo(`task_id=${parsed.task_id} articles=${parsed.articles.length}`)
    logPass('JSON structure valid')

    log('  RESULT  TC-03 PASSED')
  })
})
