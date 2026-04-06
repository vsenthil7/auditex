/**
 * Auditex Dashboard — Playwright E2E Tests
 * TC-01  Dashboard loads, form visible, no console errors
 * TC-02  Submit Document Review → appears in list → polls to COMPLETED
 * TC-03  Task detail shows report, EU AI Act accordion, Export downloads JSON
 *
 * Run from frontend/ directory:
 *   npx playwright test --reporter=list
 *
 * Log: tests/results/playwright-run-<timestamp>.log
 */

import { test, expect } from '@playwright/test'
import * as fs from 'fs'
import * as path from 'path'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname  = path.dirname(__filename)

const BASE_URL  = 'http://localhost:3000'
const POLL_MS   = 4_000   // slightly longer than app's 3s poll

// ── Log setup ─────────────────────────────────────────────────────────────────
const resultsDir = path.join(__dirname, 'results')
if (!fs.existsSync(resultsDir)) fs.mkdirSync(resultsDir, { recursive: true })
const timestamp  = new Date().toISOString().replace(/[:.]/g, '-')
const logFile    = path.join(resultsDir, `playwright-run-${timestamp}.log`)
const logStream  = fs.createWriteStream(logFile, { flags: 'a' })

function log(msg: string)          { const l = `[${new Date().toISOString()}] ${msg}`; console.log(l); logStream.write(l+'\n') }
function logStep(s: string)        { log(`  STEP  ${s}`) }
function logPass(s: string)        { log(`  PASS  ✓ ${s}`) }
function logFail(s: string, e?: unknown) { log(`  FAIL  ✗ ${s}${e?' — '+e:''}`) }
function logInfo(s: string)        { log(`  INFO  ${s}`) }
function logSuite(s: string)       { log(''); log('═'.repeat(60)); log(`  ${s}`); log('═'.repeat(60)) }

const TERMINAL = new Set(['COMPLETED', 'FAILED', 'ESCALATED'])

// ── Tests ─────────────────────────────────────────────────────────────────────
test.describe('Auditex Dashboard E2E', () => {

  test.beforeAll(() => {
    log(''); log('█'.repeat(60))
    log('  Auditex Playwright E2E  —  ' + new Date().toLocaleString())
    log('  Target: ' + BASE_URL)
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

    const consoleErrors: string[] = []
    page.on('console', m => { if (m.type() === 'error') consoleErrors.push(m.text()) })
    page.on('pageerror', e => consoleErrors.push(e.message))

    logStep('Navigate + hard reload')
    await page.goto(BASE_URL, { waitUntil: 'networkidle' })
    await page.reload({ waitUntil: 'networkidle' })
    logPass('Page loaded')

    logStep('Title contains Auditex')
    await expect(page).toHaveTitle(/Auditex/i)
    logPass('Title: ' + await page.title())

    for (const [label, loc] of [
      ['header',            page.locator('header')],
      ['Submit New Task',   page.getByText('Submit New Task')],
      ['Task Type select',  page.locator('select')],
      ['Document textarea', page.locator('textarea')],
      ['Submit button',     page.getByRole('button', { name: /Submit Task/i })],
      ['Tasks panel',       page.getByText(/^Tasks/)],
    ] as const) {
      logStep(`Check ${label} visible`)
      await expect(loc).toBeVisible()
      logPass(`${label} visible`)
    }

    logStep('Zero console errors')
    if (consoleErrors.length > 0) {
      logFail('Console errors', consoleErrors.join(' | '))
      throw new Error('Console errors: ' + consoleErrors.join(' | '))
    }
    logPass('No console errors')
    log('  RESULT  TC-01 PASSED')
  })

  // ── TC-02 ──────────────────────────────────────────────────────────────────
  test('TC-02  Submit Document Review task and poll to COMPLETED', async ({ page }) => {
    logSuite('TC-02  Submit → poll to COMPLETED')
    test.setTimeout(180_000)  // 3 min: real Claude+GPT execution takes ~60-90s

    logStep('Navigate')
    await page.goto(BASE_URL, { waitUntil: 'networkidle' })
    await page.reload({ waitUntil: 'networkidle' })
    logPass('Page loaded')

    logStep('Select document_review')
    await page.locator('select').selectOption('document_review')
    logPass('document_review selected')

    const doc = `Applicant: Jane Doe
Date of Birth: 22/07/1990
Address: 10 Downing Street, London, SW1A 2AA
Employment: Product Manager at FinTech Ltd (4 years)
Annual Salary: £85,000
Monthly Net Income: £4,900
Loan Amount Requested: £320,000
Loan Purpose: Residential mortgage
Credit Score: 740
Existing Debts: None`

    logStep('Fill document textarea')
    await page.locator('textarea').fill(doc)
    logPass('Document filled')

    logStep('Tick Completeness + Income Verification')
    await page.getByLabel('Completeness').check()
    await page.getByLabel('Income Verification').check()
    logPass('Criteria checked')

    const rowsBefore = await page.locator('button.w-full.text-left').count()
    logInfo(`Task rows before submit: ${rowsBefore}`)

    logStep('Click Submit Task')
    await page.getByRole('button', { name: /Submit Task/i }).click()
    logPass('Submit clicked')

    logStep('Wait for new row to appear (15s)')
    await expect(async () => {
      expect(await page.locator('button.w-full.text-left').count()).toBeGreaterThan(rowsBefore)
    }).toPass({ timeout: 15_000, intervals: [500] })
    logPass('New row appeared')

    // Get the task ID from the first (newest) row for targeted polling
    const firstRowText = await page.locator('button.w-full.text-left').first().textContent()
    logInfo(`Newest row text: ${firstRowText?.trim().slice(0, 80)}`)

    logStep('Poll newest row for terminal status (up to 180s)')
    let finalStatus = ''
    await expect(async () => {
      await page.waitForTimeout(POLL_MS)

      // Read ALL span texts inside the first row to find the status badge
      const firstRow = page.locator('button.w-full.text-left').first()
      const spans = await firstRow.locator('span').allTextContents()
      logInfo(`Row spans: [${spans.map(s => s.trim()).join(', ')}]`)

      const statusSpan = spans.find(s => TERMINAL.has(s.trim()))
      if (statusSpan) {
        finalStatus = statusSpan.trim()
        logInfo(`Terminal status found: ${finalStatus}`)
      }
      expect(statusSpan).toBeTruthy()
    }).toPass({ timeout: 180_000, intervals: [POLL_MS] })

    if (finalStatus === 'COMPLETED') {
      logPass(`Task reached COMPLETED`)
    } else {
      logFail(`Task ended with: ${finalStatus}`)
      throw new Error(`Expected COMPLETED, got: ${finalStatus}`)
    }
    log('  RESULT  TC-02 PASSED')
  })

  // ── TC-03 ──────────────────────────────────────────────────────────────────
  test('TC-03  Task detail shows report and export downloads JSON', async ({ page }) => {
    logSuite('TC-03  Report visible + export downloads JSON')
    test.setTimeout(120_000)

    logStep('Navigate')
    await page.goto(BASE_URL, { waitUntil: 'networkidle' })
    await page.reload({ waitUntil: 'networkidle' })
    logPass('Page loaded')

    logStep('Wait for COMPLETED task in list (30s)')
    await expect(
      page.locator('button.w-full.text-left span').filter({ hasText: /^COMPLETED$/ }).first()
    ).toBeVisible({ timeout: 30_000 })
    logPass('COMPLETED task visible')

    logStep('Click first COMPLETED row')
    await page.locator('button.w-full.text-left')
      .filter({ has: page.locator('span', { hasText: /^COMPLETED$/ }) })
      .first().click()
    logPass('Clicked row')

    logStep('Wait for TaskDetail panel (task ID visible)')
    await expect(page.locator('p.font-mono').first()).toBeVisible({ timeout: 10_000 })
    const taskId = (await page.locator('p.font-mono').first().textContent())?.trim()
    logInfo(`Selected task: ${taskId}`)

    logStep('Wait for Plain English Summary (60s)')
    await expect(page.getByText('Plain English Summary')).toBeVisible({ timeout: 60_000 })
    logPass('Plain English Summary visible')

    logStep('Check EU AI Act Compliance section')
    await expect(page.getByText('EU AI Act Compliance')).toBeVisible()
    logPass('EU AI Act section visible')

    logStep('Expand first article accordion')
    const articleBtn = page.locator('button').filter({ hasText: /Article/ }).first()
    await expect(articleBtn).toBeVisible({ timeout: 10_000 })
    const articleTitle = (await articleBtn.textContent())?.trim().slice(0, 60)
    logInfo(`First article: ${articleTitle}`)
    await articleBtn.click()
    logPass('Article expanded')

    logStep('Click Export and capture download')
    const [download] = await Promise.all([
      page.waitForEvent('download', { timeout: 20_000 }),
      page.getByRole('button', { name: /Export EU AI Act JSON/i }).click(),
    ])
    const filename = download.suggestedFilename()
    logInfo(`Downloaded: ${filename}`)

    logStep('Verify filename pattern')
    expect(filename).toMatch(/^auditex-report-.+\.json$/)
    logPass(`Filename correct: ${filename}`)

    logStep('Save + validate JSON structure')
    const savePath = path.join(resultsDir, filename)
    await download.saveAs(savePath)
    const parsed = JSON.parse(fs.readFileSync(savePath, 'utf-8'))
    expect(parsed).toHaveProperty('task_id')
    expect(Array.isArray(parsed.articles)).toBe(true)
    logInfo(`task_id=${parsed.task_id}, articles=${parsed.articles.length}`)
    logPass('JSON valid')

    log('  RESULT  TC-03 PASSED')
  })
})
