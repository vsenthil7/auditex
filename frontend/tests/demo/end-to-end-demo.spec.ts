/**
 * Auditex end-to-end captioned demo - submits real tasks through the real backend.
 * For each test case: caption -> submit form -> watch pipeline run -> open result -> next.
 * No mocking. Real Anthropic and OpenAI calls. Real Vertex consensus. Real timing.
 *
 * Run: cd frontend; npx playwright test tests/demo/end-to-end-demo.spec.ts --headed --project=chromium
 * Out: frontend/test-results/.../video.webm (then copied to demo/)
 */
import { test, expect } from '@playwright/test'
import { showCaption, hideCaption, showTitleCard, READ_SHORT } from './caption-overlay'

const BASE = 'http://localhost:3000'

// Lower / raise the black shutter so the page is hidden during caption transitions
// and visible during form interactions and result reveal.
async function lowerShutter(page: any) {
  await page.evaluate(() => {
    const s = document.getElementById('demo-shutter') as HTMLElement | null
    if (s) {
      s.style.transition = 'opacity 0.25s ease'
      s.style.opacity = '0'
      setTimeout(() => { s.style.pointerEvents = 'none' }, 260)
    }
  })
  await page.waitForTimeout(280)
}

async function raiseShutter(page: any) {
  await page.evaluate(() => {
    const s = document.getElementById('demo-shutter') as HTMLElement | null
    if (s) {
      s.style.pointerEvents = 'auto'
      s.style.transition = 'opacity 0.2s ease'
      s.style.opacity = '1'
    }
  })
  await page.waitForTimeout(220)
}

interface DemoCase {
  scene: string
  title: string
  given: string
  when: string
  then: string
  expected: string
  taskType: string  // e.g. contract_check
  document: string  // text to paste into the textarea
  criteria: string[]  // labels to tick
}

const CASES: DemoCase[] = [
  {
    scene: 'TC-DEMO-1 of 3',
    title: 'Contract Check - APPROVE path',
    given: 'A clean Data Processing Agreement that fully covers Article 28 GDPR',
    when: 'Compliance officer submits it for contract_check',
    then: 'Pipeline runs Executor + 3 Reviewers, BFT consensus reaches APPROVE',
    expected: 'Status COMPLETED with executor + reviewers + vertex hash visible',
    taskType: 'contract_check',
    criteria: ['Completeness'],
    document: `Data Processing Agreement - TechCorp Ltd & Vendor Services Inc.

1. Scope: Vendor processes personal data on behalf of TechCorp under this DPA.
2. Purpose: Payment processing for e-commerce transactions (Art. 28 GDPR).
3. Categories: Customer name, email, billing address, order history.
4. Retention: 6 years post-transaction; deleted thereafter.
5. Sub-processors: Annex A, with 30-day prior notification of changes.
6. Security: AES-256 at rest, TLS 1.3 in transit, SOC 2 Type II certified.
7. Data subject rights: access, rectification, erasure within 30 days.
8. Breach notification: within 24 hours of any incident.
9. International transfers: UK-EU Adequacy + SCCs.
10. Audit rights: annual with 30-day notice.

This DPA is complete and all Article 28 items are explicitly addressed.`,
  },
  {
    scene: 'TC-DEMO-2 of 3',
    title: 'Risk Analysis - REJECT path',
    given: 'A high-risk loan application with impossible income claim',
    when: 'Compliance officer submits it for risk_analysis',
    then: 'Pipeline detects anomaly, all 3 reviewers vote REJECT',
    expected: 'Status COMPLETED, recommendation REJECT, reasoning explains the red flag',
    taskType: 'risk_analysis',
    criteria: ['Income Verification', 'Risk Assessment'],
    document: `Loan Application - Applicant ID 88472

Stated annual income: GBP 4,500,000
Stated employer: TechCorp Ltd (entry-level role, started 2 weeks ago)
Loan amount requested: GBP 12,000,000 unsecured
Term: 6 months bullet repayment
Stated assets: cryptocurrency holdings (no exchange records provided)
Stated purpose: investment in private offshore venture
Provided documentation: 1 page CV, no payslips, no bank statements, no tax returns
Credit history: no record found in standard UK credit reference agencies

This application has multiple red flags consistent with money laundering or fraud.`,
  },
  {
    scene: 'TC-DEMO-3 of 3',
    title: 'Document Review - REQUEST_AMENDMENTS path',
    given: 'An almost-complete employment verification missing one key field',
    when: 'Compliance officer submits it for document_review',
    then: 'Pipeline flags missing field, reviewers vote REQUEST_AMENDMENTS',
    expected: 'Status COMPLETED, recommendation REQUEST_AMENDMENTS, specific gap noted',
    taskType: 'document_review',
    criteria: ['Employment Verification', 'Completeness'],
    document: `Employment Verification - Subject: Jane Smith

Employer: Northwind Logistics Ltd
Position: Senior Operations Analyst
Start date: 12 February 2024
Employment type: Full-time, permanent
Annual salary: 
Hours: 40 per week
Manager: Robert Chen (rchen@northwindlogistics.example)
HR contact: Sarah Patel (hr@northwindlogistics.example)
Letter dated and signed: 15 March 2026

Note: salary field is blank above. The verifier must request this before approval.`,
  },
]

test.describe('Auditex End-to-End Captioned Demo', () => {
  test('Real submission walkthrough across 3 outcome paths', async ({ page }) => {
    test.setTimeout(30 * 60 * 1000)  // 30 min budget; real LLM calls

    // Inject a black shutter that hides the page until we explicitly raise it.
    // Prevents the dashboard from flashing during navigations and caption transitions.
    await page.addInitScript(() => {
      const id = 'demo-shutter'
      if (document.getElementById(id)) return
      const s = document.createElement('div')
      s.id = id
      s.style.cssText = 'position:fixed;inset:0;z-index:2147483646;background:#0f172a;transition:opacity 0.25s ease;opacity:1;'
      const body = document.body || document.documentElement
      if (body) body.appendChild(s)
      else document.addEventListener('DOMContentLoaded', () => document.body.appendChild(s))
    })

    await page.goto(BASE)
    await page.waitForLoadState("networkidle", { timeout: 30000 }).catch(() => {})

    await showTitleCard(page, 'Auditex', 'EU AI Act compliance audit pipeline. End-to-end demo: 3 real submissions, 3 outcome paths, no mocking. DoraHacks BUIDL #43345.', 4500)

    for (let i = 0; i < CASES.length; i++) {
      const c = CASES[i]

      // Caption screen for this test case
      await showCaption(page, {
        scene: c.scene,
        title: c.title,
        given: c.given,
        when: c.when,
        then: c.then,
        testData: ['Task type: ' + c.taskType, 'Criteria: ' + c.criteria.join(', ')],
        expected: c.expected,
        holdMs: 4500,
      })
      await hideCaption(page)

      // Make sure dashboard is visible (not stuck on prev task detail)
      const submitFormHeading = page.getByRole('heading', { name: /Submit New Task/i })
      if (!(await submitFormHeading.isVisible().catch(() => false))) {
        await page.goto(BASE)
        await page.waitForTimeout(800)
      }

      // Lower the black shutter now that we are about to show real UI interactions.
      await lowerShutter(page)

      // 1) Select task type - scroll form into view + hover dropdown so viewer sees it
      const formHeading = page.getByRole('heading', { name: /Submit New Task/i })
      await formHeading.scrollIntoViewIfNeeded()
      await page.waitForTimeout(700)
      const taskSelect = page.locator('select')
      await taskSelect.scrollIntoViewIfNeeded()
      await taskSelect.hover()
      await page.waitForTimeout(800)
      await taskSelect.selectOption(c.taskType)
      await page.waitForTimeout(1200)  // viewer reads the selected option

      // 2) Type the document - scroll textarea into view, click, then fill in real-time
      const textarea = page.locator('textarea')
      await textarea.scrollIntoViewIfNeeded()
      await textarea.hover()
      await page.waitForTimeout(500)
      await textarea.click()
      // Use type() not fill() so the keystrokes are visible in the recording
      await textarea.type(c.document, { delay: 8 })
      await page.waitForTimeout(900)

      // 3) Tick criteria checkboxes - scroll into view + visible hover before each tick
      for (const label of c.criteria) {
        const cb = page.locator(`label:has-text("${label}") input[type="checkbox"]`)
        await cb.scrollIntoViewIfNeeded()
        await cb.hover()
        await page.waitForTimeout(450)
        if (!(await cb.isChecked().catch(() => false))) {
          await cb.check({ force: true })
          await page.waitForTimeout(550)
        }
      }
      await page.waitForTimeout(700)

      // 4) Click Submit Task - scroll button into view + hover
      const submitBtn = page.getByRole('button', { name: /^Submit Task$/i })
      await submitBtn.scrollIntoViewIfNeeded()
      await submitBtn.hover()
      await page.waitForTimeout(700)
      // Capture the freshly-created task id from the POST response
      const submitResponse = page.waitForResponse((r) => r.url().includes('/api/v1/tasks') && r.request().method() === 'POST' && r.status() === 201, { timeout: 30000 })
      await submitBtn.click()
      const resp = await submitResponse
      const respJson = await resp.json()
      const newTaskId = respJson.task_id as string
      console.log('[demo] submitted task: ' + newTaskId + ' (' + c.taskType + ')')
      await page.waitForTimeout(1500)

      // 5) Locate the just-submitted task in the list by its 8-char id prefix.
      // TaskList renders {task_id.slice(0, 8)} so we match on that to avoid picking up
      // an older COMPLETED task from the previous test case.
      const idPrefix = newTaskId.slice(0, 8)
      const myTaskRow = page.locator('button.w-full.text-left').filter({ hasText: idPrefix })
      await expect(myTaskRow).toBeVisible({ timeout: 15000 })
      await myTaskRow.scrollIntoViewIfNeeded()
      await page.waitForTimeout(800)
      await myTaskRow.click()
      await page.waitForTimeout(1000)

      // 6) Wait for COMPLETED status on this specific task
      const detail = page.locator('[data-testid="task-detail"]')
      await expect(detail).toBeVisible({ timeout: 10000 })
      await expect(myTaskRow).toContainText(/COMPLETED/i, { timeout: 90 * 1000 })

      // 7a) Wait for executor block to populate inside the detail panel.
      // The list shows COMPLETED ~3s before /tasks/{id} returns full executor + review + vertex.
      await expect(detail.locator('text=/Step 2/i').first()).toBeVisible({ timeout: 30000 })
      await page.waitForTimeout(1500)

      // 7b) Expand all 5 pipeline step accordions first (quick pass: Submit/Execute/Review/Vertex/Report).
      const steps = detail.locator('button', { hasText: /^Step [1-5]/ })
      const stepCount = await steps.count()
      for (let s = 0; s < Math.min(stepCount, 5); s++) {
        await steps.nth(s).scrollIntoViewIfNeeded()
        await page.waitForTimeout(300)
        await steps.nth(s).click()
        await page.waitForTimeout(450)
      }

      // 7c) Now visit each step in sequence with adequate read time. Step 2 (executor)
      // and Step 3 (reviewers) get extra time because they have more content.
      const stepReadTimes = [2200, 4500, 4000, 3500, 3500]  // ms per step (Step 1..5)
      for (let s = 0; s < Math.min(stepCount, 5); s++) {
        await steps.nth(s).scrollIntoViewIfNeeded()
        await page.waitForTimeout(stepReadTimes[s] || 3000)
      }

      // 7d) Final pass: scroll smoothly from top to bottom of the panel so viewer
      // sees Step 5 compliance report fully (including Articles 9/13/17 sub-content).
      const detailHeight = await detail.evaluate((el) => el.scrollHeight)
      const detailViewport = await detail.evaluate((el) => el.clientHeight)
      const maxScroll = Math.max(0, detailHeight - detailViewport)
      await detail.evaluate((el) => el.scrollTo({ top: 0, behavior: 'smooth' }))
      await page.waitForTimeout(800)
      // Scroll to bottom in 6-7 visible steps
      const stepPx = Math.max(200, Math.ceil(maxScroll / 6))
      for (let y = 0; y <= maxScroll; y += stepPx) {
        await detail.evaluate((el, pos) => el.scrollTo({ top: pos, behavior: 'smooth' }), y)
        await page.waitForTimeout(1300)
      }
      // Linger on the bottom (Step 5 - compliance report) for 3.5s
      await detail.evaluate((el) => el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' }))
      await page.waitForTimeout(3500)

      // Raise the black shutter so the next caption (or the closing card) paints over it cleanly.
      await raiseShutter(page)

      // Buffer between submissions to avoid rate limiter on the API key
      if (i < CASES.length - 1) await page.waitForTimeout(12000)
    }  // end for-each case

    await showTitleCard(page, 'Auditex', 'github.com/vsenthil7/auditex   |   DoraHacks BUIDL #43345   |   See ENTERPRISE-GAP-REGISTER.md for honest current-state disclosure.', 4500)
  })
})
