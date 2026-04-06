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

const BASE_URL = 'http://localhost:3000'
const POLL_MS  = 5_000   // wait between status checks

// ── Log setup ─────────────────────────────────────────────────────────────────
const resultsDir = path.join(__dirname, 'results')
if (!fs.existsSync(resultsDir)) fs.mkdirSync(resultsDir, { recursive: true })
const timestamp  = new Date().toISOString().replace(/[:.]/g, '-')
const logFile    = path.join(resultsDir, `playwright-run-${timestamp}.log`)
const logStream  = fs.createWriteStream(logFile, { flags: 'a' })

function log(msg: string)  { const l=`[${new Date().toISOString()}] ${msg}`; console.log(l); logStream.write(l+'\n') }
function logStep(s: string){ log(`  STEP  ${s}`) }
function logPass(s: string){ log(`  PASS  ✓ ${s}`) }
function logFail(s: string, e?: unknown){ log(`  FAIL  ✗ ${s}${e?' — '+e:''}`) }
function logInfo(s: string){ log(`  INFO  ${s}`) }
function logSuite(s: string){ log(''); log('═'.repeat(60)); log(`  ${s}`); log('═'.repeat(60)) }

const TERMINAL = new Set(['COMPLETED','FAILED','ESCALATED'])

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
    page.on('console', m => { if (m.type()==='error') consoleErrors.push(m.text()) })
    page.on('pageerror', e => consoleErrors.push(e.message))

    logStep('Navigate + hard reload')
    await page.goto(BASE_URL, { waitUntil: 'networkidle' })
    await page.reload({ waitUntil: 'networkidle' })
    logPass('Page loaded')

    logStep('Title contains Auditex')
    await expect(page).toHaveTitle(/Auditex/i)
    logPass('Title: ' + await page.title())

    const checks: [string, any][] = [
      ['header',            page.locator('header')],
      ['Submit New Task',   page.getByText('Submit New Task')],
      ['Task Type select',  page.locator('select')],
      ['Document textarea', page.locator('textarea')],
      ['Submit button',     page.getByRole('button', { name: /Submit Task/i })],
      ['Tasks panel',       page.getByText(/^Tasks/)],
    ]
    for (const [label, loc] of checks) {
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
    test.setTimeout(240_000)  // 4 min: real Claude+GPT takes ~60-120s

    logStep('Navigate')
    await page.goto(BASE_URL, { waitUntil: 'networkidle' })
    await page.reload({ waitUntil: 'networkidle' })
    logPass('Page loaded')

    logStep('Select document_review')
    await page.locator('select').selectOption('document_review')
    logPass('document_review selected')

    const doc = `Applicant: Jane Doe
Date of Birth: 22/07/1990
Address: 10 Downing Street London SW1A 2AA
Employment: Product Manager at FinTech Ltd 4 years
Annual Salary: 85000 GBP
Monthly Net Income: 4900 GBP
Loan Amount Requested: 320000 GBP
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

    logStep('Wait for new row (15s)')
    await expect(async () => {
      expect(await page.locator('button.w-full.text-left').count()).toBeGreaterThan(rowsBefore)
    }).toPass({ timeout: 15_000, intervals: [500] })
    logPass('New row appeared')

    // ── Plain while-loop polling — logs every cycle, no toPass() nesting ──
    logStep('Poll for terminal status every 5s (up to 4 min)...')
    const deadline = Date.now() + 230_000
    let finalStatus = ''
    let elapsed = 0

    while (Date.now() < deadline) {
      await page.waitForTimeout(POLL_MS)
      elapsed += POLL_MS

      try {
        const firstRow  = page.locator('button.w-full.text-left').first()
        const spans     = await firstRow.locator('span').allTextContents()
        const cleaned   = spans.map(s => s.trim()).filter(Boolean)
        logInfo(`[${Math.round(elapsed/1000)}s] spans: [${cleaned.join(', ')}]`)

        const terminal = cleaned.find(s => TERMINAL.has(s))
        if (terminal) {
          finalStatus = terminal
          logInfo(`Terminal status: ${finalStatus}`)
          break
        }
      } catch (e) {
        logInfo(`Poll error (will retry): ${e}`)
      }
    }

    if (finalStatus === 'COMPLETED') {
      logPass('Task reached COMPLETED')
      log('  RESULT  TC-02 PASSED')
    } else if (finalStatus === 'FAILED' || finalStatus === 'ESCALATED') {
      logFail(`Task ended with: ${finalStatus}`)
      throw new Error(`Task ended with ${finalStatus} — check backend logs`)
    } else {
      logFail('Timed out waiting for COMPLETED (4 min elapsed)')
      throw new Error('TC-02 timed out — task did not complete within 4 minutes')
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

    logStep('Wait for TaskDetail panel')
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
    logInfo('First article: ' + (await articleBtn.textContent())?.trim().slice(0, 60))
    await articleBtn.click()
    logPass('Article expanded')

    logStep('Click Export + capture download')
    const [download] = await Promise.all([
      page.waitForEvent('download', { timeout: 20_000 }),
      page.getByRole('button', { name: /Export EU AI Act JSON/i }).click(),
    ])
    const filename = download.suggestedFilename()
    logInfo(`Downloaded: ${filename}`)

    expect(filename).toMatch(/^auditex-report-.+\.json$/)
    logPass(`Filename correct: ${filename}`)

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
