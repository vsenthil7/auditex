/**
 * Auditex end-to-end captioned demo - 6-scenario matrix.
 * 3 task types x 2 paths each (no-HIL direct + HIL via human) = 6 scenarios.
 *
 * Every scenario shows full pipeline + Vertex sign+verify. No blank screens between scenarios -
 * each caption paints directly over the previous task's detail panel.
 *
 * Run: cd frontend; npx playwright test tests/demo/end-to-end-demo.spec.ts --headed --project=chromium
 * Out: frontend/test-results/.../video.webm (then copied to demo/)
 */
import { test, expect } from '@playwright/test'
import { showCaption, hideCaption, showTitleCard, READ_SHORT } from './caption-overlay'

const BASE = 'http://localhost:3000'
const API = 'http://localhost:8000'
const API_KEY = 'auditex-test-key-phase2'

interface Scenario {
  scene: string
  title: string
  given: string
  when: string
  then: string
  expected: string
  taskType: string
  document: string
  criteria: string[]
  hil: boolean
  hilDecision?: 'APPROVE' | 'REJECT' | 'REQUEST_AMENDMENTS'
}

const SCENARIOS: Scenario[] = [
  {
    scene: 'TC-1 of 6',
    title: 'Contract Check - Auto APPROVE',
    given: 'A clean DPA covering Article 28 GDPR. No human oversight required.',
    when: 'Compliance officer submits for contract_check (HIL policy disabled)',
    then: 'Pipeline + 3 reviewers reach BFT consensus APPROVE, signed Vertex event recorded',
    expected: 'COMPLETED with executor + reviewers + Vertex hash + signed report VALID',
    taskType: 'contract_check',
    criteria: ['Completeness'],
    hil: false,
    document: `Data Processing Agreement - TechCorp Ltd & Vendor Services Inc.

1. Scope: Vendor processes personal data on behalf of TechCorp under this DPA.
2. Purpose: Payment processing for e-commerce transactions (Art. 28 GDPR).
3. Categories: Customer name, email, billing address, order history.
4. Retention: 6 years post-transaction; deleted thereafter.
5. Sub-processors: Annex A, with 30-day prior notification of changes.
6. Security: AES-256 at rest, TLS 1.3 in transit, SOC 2 Type II certified.
7. Data subject rights: access, rectification, erasure within 30 days.
8. Breach notification: within 24 hours of any incident.

This DPA is complete and all Article 28 items are explicitly addressed.`,
  },
  {
    scene: 'TC-2 of 6',
    title: 'Contract Check - Human APPROVE (Article 14)',
    given: 'Same DPA, but contract_check policy now requires human oversight',
    when: 'Compliance officer submits, then reviewer approves via Human Review queue',
    then: 'Task pauses at AWAITING_HUMAN_REVIEW, finalises after human APPROVE',
    expected: 'COMPLETED with human_decisions_count: 1, signed Vertex event includes human signature',
    taskType: 'contract_check',
    criteria: ['Completeness'],
    hil: true,
    hilDecision: 'APPROVE',
    document: `Data Processing Agreement - HIL Demo - Article 14 Path

1. Scope: Vendor processes personal data under Article 28.
2. Purpose: Demonstrate Article 14 human oversight on contract_check.
3. Categories: Standard contact and transactional data.
4. Retention: 6 years post-transaction.
5. Sub-processors: Annex A, 30-day prior notification.
6. Security: AES-256 at rest, TLS 1.3 in transit.

Policy-flagged for human review.`,
  },
  {
    scene: 'TC-3 of 6',
    title: 'Risk Analysis - Auto REJECT',
    given: 'High-risk loan with impossible income + no docs. No human required.',
    when: 'Compliance officer submits for risk_analysis (HIL policy disabled)',
    then: 'Pipeline detects anomaly, 3 reviewers vote REJECT',
    expected: 'COMPLETED REJECT with red flag reasoning + signed Vertex event VALID',
    taskType: 'risk_analysis',
    criteria: ['Income Verification', 'Risk Assessment'],
    hil: false,
    document: `Loan Application - Applicant ID 88472

Stated annual income: GBP 4,500,000
Stated employer: TechCorp Ltd (entry-level role, started 2 weeks ago)
Loan amount requested: GBP 12,000,000 unsecured
Term: 6 months bullet repayment
Stated assets: cryptocurrency holdings (no exchange records provided)
Stated purpose: investment in private offshore venture
Provided documentation: 1 page CV, no payslips, no bank statements, no tax returns
Credit history: no record found in standard UK credit reference agencies`,
  },
  {
    scene: 'TC-4 of 6',
    title: 'Risk Analysis - Human REJECT (Article 14)',
    given: 'Borderline-risk loan flagged for senior human review under Article 14',
    when: 'Submit, then reviewer overrides AI consensus with REJECT',
    then: 'Human REJECT decision binds task to COMPLETED with REJECT recommendation',
    expected: 'COMPLETED, recorded human_decisions_count: 1, Vertex includes human REJECT',
    taskType: 'risk_analysis',
    criteria: ['Risk Assessment'],
    hil: true,
    hilDecision: 'REJECT',
    document: `Loan Application - HIL Senior Review Required

Applicant: SmallCorp Holdings Ltd
Stated revenue: GBP 850k/year
Loan amount: GBP 2,000,000 unsecured
Term: 18 months
Documentation: 6mo bank statements + 2yr accounts provided
Credit history: clean, no flags

Article 14 oversight requested by Risk Committee policy.`,
  },
  {
    scene: 'TC-5 of 6',
    title: 'Document Review - Auto REQUEST_AMENDMENTS',
    given: 'Almost-complete employment verification missing one key field',
    when: 'Submit for document_review (HIL policy disabled)',
    then: 'Pipeline flags missing field, reviewers vote REQUEST_AMENDMENTS',
    expected: 'COMPLETED with REQUEST_AMENDMENTS + specific gap noted + Vertex VALID',
    taskType: 'document_review',
    criteria: ['Employment Verification', 'Completeness'],
    hil: false,
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

Note: salary field is blank. Verifier must request this before approval.`,
  },
  {
    scene: 'TC-6 of 6',
    title: 'Document Review - Human REQUEST_AMENDMENTS (Article 14)',
    given: 'Document review with HIL policy enabled - human reviewer requests fixes',
    when: 'Submit, then reviewer manually requests amendments',
    then: 'Task pauses, then finalises with human REQUEST_AMENDMENTS',
    expected: 'COMPLETED with human_decisions_count: 1, Vertex VALID',
    taskType: 'document_review',
    criteria: ['Completeness'],
    hil: true,
    hilDecision: 'REQUEST_AMENDMENTS',
    document: `Employment Verification - HIL Manual Review

Employer: Acme Holdings Ltd
Position: Operations Lead
Start date: 1 March 2025
Annual salary: GBP 75,000
Manager: Susan Lee
Letter dated: 10 April 2026

Reviewer to flag missing fields manually.`,
  },
]

async function setPolicy(request: any, taskType: string, required: boolean) {
  const body = { task_type: taskType, required, n_required: 1, m_total: 1, timeout_minutes: null, auto_commit_on_timeout: false }
  await request.put(`${API}/api/v1/human-oversight-policies/${taskType}`, {
    headers: { 'X-API-Key': API_KEY, 'Content-Type': 'application/json' },
    data: body,
  })
}

test.describe('Auditex 6-Scenario Captioned Demo', () => {
  test('3 task types x 2 paths (no-HIL + HIL) = 6 scenarios with Vertex sign+verify', async ({ page, request }) => {
    test.setTimeout(60 * 60 * 1000)  // 60 min budget; 6 LLM scenarios + Vertex verify each

    // Initial nav
    await page.goto(BASE)
    await page.waitForLoadState('networkidle', { timeout: 30000 }).catch(() => {})

    // Title card opens the demo
    await showTitleCard(page, 'Auditex', 'EU AI Act compliance audit pipeline. 6 scenarios: 3 task types x (Auto + Human-in-Loop). Tamper-proof Vertex consensus on every event. DoraHacks BUIDL #43345.', 4500)

    for (let i = 0; i < SCENARIOS.length; i++) {
      const sc = SCENARIOS[i]

      // Pre-set policy state for this scenario (disable for auto, enable for HIL)
      await setPolicy(request, sc.taskType, sc.hil)
      await page.waitForTimeout(400)

      // Caption paints directly over previous detail (no shutter -> no blank screen)
      await showCaption(page, {
        scene: sc.scene,
        title: sc.title,
        given: sc.given,
        when: sc.when,
        then: sc.then,
        testData: ['Task type: ' + sc.taskType, 'HIL: ' + (sc.hil ? 'ENABLED (' + sc.hilDecision + ')' : 'disabled'), 'Criteria: ' + sc.criteria.join(', ')],
        expected: sc.expected,
        holdMs: 3500,
      })
      await hideCaption(page)

      // Make sure dashboard is visible
      const submitFormHeading = page.getByRole('heading', { name: /Submit New Task/i })
      if (!(await submitFormHeading.isVisible().catch(() => false))) {
        // Click the dashboard tab if available, else hard-nav
        const tabDash = page.locator('[data-testid="tab-dashboard"]')
        if (await tabDash.isVisible().catch(() => false)) {
          await tabDash.click()
          await page.waitForTimeout(500)
        } else {
          await page.goto(BASE)
          await page.waitForTimeout(500)
        }
      }

      // 1) Select task type
      const formHeading = page.getByRole('heading', { name: /Submit New Task/i })
      await formHeading.scrollIntoViewIfNeeded()
      await page.waitForTimeout(300)
      const taskSelect = page.locator('select')
      await taskSelect.scrollIntoViewIfNeeded()
      await taskSelect.selectOption(sc.taskType)
      await page.waitForTimeout(500)

      // 2) Type document
      const textarea = page.locator('textarea')
      await textarea.scrollIntoViewIfNeeded()
      await textarea.click()
      // Clear any leftover text first
      await page.keyboard.press('Control+A')
      await page.keyboard.press('Delete')
      await textarea.type(sc.document, { delay: 4 })
      await page.waitForTimeout(300)

      // 3) Tick criteria
      for (const label of sc.criteria) {
        const cb = page.locator(`label:has-text("${label}") input[type="checkbox"]`)
        await cb.scrollIntoViewIfNeeded()
        if (!(await cb.isChecked().catch(() => false))) {
          await cb.check({ force: true })
          await page.waitForTimeout(200)
        }
      }
      await page.waitForTimeout(300)

      // 4) Submit
      const submitBtn = page.getByRole('button', { name: /^Submit Task$/i })
      await submitBtn.scrollIntoViewIfNeeded()
      const submitResponse = page.waitForResponse((r) => r.url().includes('/api/v1/tasks') && r.request().method() === 'POST' && r.status() === 201, { timeout: 30000 })
      await submitBtn.click()
      const resp = await submitResponse
      const respJson = await resp.json()
      const newTaskId = respJson.task_id as string
      const idPrefix = newTaskId.slice(0, 8)
      console.log('[demo] ' + sc.scene + ' submitted: ' + newTaskId + ' (' + sc.taskType + ', hil=' + sc.hil + ')')
      await page.waitForTimeout(800)

      // 5) Find the row by id prefix
      const myTaskRow = page.locator('button.w-full.text-left').filter({ hasText: idPrefix })
      await expect(myTaskRow).toBeVisible({ timeout: 15000 })
      await myTaskRow.scrollIntoViewIfNeeded()
      await page.waitForTimeout(500)

      if (sc.hil) {
        // HIL path: wait for NEEDS HUMAN, then go to Human Review tab and decide
        await myTaskRow.click()  // open detail so viewer sees task is being worked on
        await page.waitForTimeout(800)
        await expect(myTaskRow).toContainText(/NEEDS.*HUMAN/i, { timeout: 120 * 1000 })
        await page.waitForTimeout(2000)  // viewer reads the amber pulse

        // Click Human Review tab
        const tabHumanReview = page.locator('[data-testid="tab-human-review"]')
        await tabHumanReview.scrollIntoViewIfNeeded()
        await tabHumanReview.click()
        await page.waitForTimeout(800)

        // Select task in queue
        const queueRow = page.locator(`[data-testid="queue-task-${idPrefix}"]`)
        await expect(queueRow).toBeVisible({ timeout: 10000 })
        await queueRow.click()
        await page.waitForTimeout(800)

        // Fill reviewer name + reason
        const reviewedBy = page.locator('[data-testid="decision-reviewed-by"]')
        await reviewedBy.click()
        await reviewedBy.type('Aoife O\'Connor', { delay: 18 })
        await page.waitForTimeout(400)
        const reasonField = page.locator('[data-testid="decision-reason"]')
        await reasonField.click()
        const reasonText =
          sc.hilDecision === 'APPROVE' ? 'Article 14 oversight - terms verified, approved.'
          : sc.hilDecision === 'REJECT' ? 'Article 14 oversight - risk too high, rejected.'
          : 'Article 14 oversight - requires amendments before approval.'
        await reasonField.type(reasonText, { delay: 8 })
        await page.waitForTimeout(500)

        // Click decision button (APPROVE / REJECT / REQUEST_AMENDMENTS)
        const decisionBtn = page.locator(`[data-testid="decision-${sc.hilDecision}"]`)
        await decisionBtn.scrollIntoViewIfNeeded()
        await decisionBtn.click()
        await page.waitForTimeout(400)

        // Submit decision
        const submitDecision = page.locator('[data-testid="decision-submit"]')
        await submitDecision.scrollIntoViewIfNeeded()
        await submitDecision.click()
        await page.waitForTimeout(800)

        // Wait for feedback then go back to dashboard
        const decisionFeedback = page.locator('[data-testid="decision-feedback"]')
        await expect(decisionFeedback).toBeVisible({ timeout: 15000 })
        await page.waitForTimeout(1500)

        const tabDashboard = page.locator('[data-testid="tab-dashboard"]')
        await tabDashboard.click()
        await page.waitForTimeout(800)
      }

      // 6) Wait for COMPLETED on this task (works for both HIL and non-HIL paths)
      const myRowAfter = page.locator('button.w-full.text-left').filter({ hasText: idPrefix })
      await expect(myRowAfter).toBeVisible({ timeout: 10000 })
      await myRowAfter.scrollIntoViewIfNeeded()
      await expect(myRowAfter).toContainText(/COMPLETED/i, { timeout: 120 * 1000 })
      await myRowAfter.click()
      await page.waitForTimeout(800)

      // 7) Detail panel: wait for executor block
      const detail = page.locator('[data-testid="task-detail"]')
      await expect(detail).toBeVisible({ timeout: 10000 })
      await expect(detail.locator('text=/Step 2/i').first()).toBeVisible({ timeout: 30000 })
      await page.waitForTimeout(800)

      // 8) Expand all 5 step accordions, briefly visit each
      const steps = detail.locator('button', { hasText: /^Step [1-5]/ })
      const stepCount = await steps.count()
      for (let s = 0; s < Math.min(stepCount, 5); s++) {
        await steps.nth(s).scrollIntoViewIfNeeded()
        await page.waitForTimeout(150)
        await steps.nth(s).click()
        await page.waitForTimeout(250)
      }

      // 9) Visit each step with read time (compressed from earlier version)
      const stepReadTimes = [1500, 3000, 2500, 2200, 3500]  // Step 5 (report) gets longer dwell
      for (let s = 0; s < Math.min(stepCount, 5); s++) {
        await steps.nth(s).scrollIntoViewIfNeeded()
        await page.waitForTimeout(stepReadTimes[s] || 2000)
      }

      // 10) Scroll to bottom (Step 5 - compliance report)
      await detail.evaluate((el) => el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' }))
      await page.waitForTimeout(2200)

      // 10b) Step 5 hard checks: re-expand if it collapsed, then dwell on report content
      // Find the Step 5 button by index (last) and ensure it's expanded by clicking only if needed.
      // Simpler: click it explicitly so accordion stays open.
      if (stepCount >= 5) {
        const stepFive = steps.nth(4)
        await stepFive.scrollIntoViewIfNeeded()
        // Check if compliance report content is visible; if not, click to expand
        const reportContent = detail.locator('[data-testid="eu-ai-act-compliance"]')
        if (!(await reportContent.isVisible().catch(() => false))) {
          await stepFive.click()
          await page.waitForTimeout(400)
        }
        await reportContent.scrollIntoViewIfNeeded().catch(() => {})
        await page.waitForTimeout(2000)
      }

      // 11) Vertex sign + verify (THE show-runner)
      const signBtn = detail.locator('[data-testid="sign-report-button"]')
      if (await signBtn.isVisible().catch(() => false)) {
        await signBtn.scrollIntoViewIfNeeded()
        await page.waitForTimeout(400)
        await signBtn.click()
        await page.waitForTimeout(1800)

        const signedDetails = detail.locator('[data-testid="signed-report-details"]')
        if (await signedDetails.isVisible().catch(() => false)) {
          await signedDetails.scrollIntoViewIfNeeded()
          await page.waitForTimeout(1500)
        }

        const verifyBtn = detail.locator('[data-testid="verify-proof-button"]')
        if (await verifyBtn.isVisible().catch(() => false)) {
          await verifyBtn.scrollIntoViewIfNeeded()
          await page.waitForTimeout(400)
          await verifyBtn.click()
          await page.waitForTimeout(1800)

          const verifyResultPanel = detail.locator('[data-testid="verify-result-panel"]')
          if (await verifyResultPanel.isVisible().catch(() => false)) {
            await verifyResultPanel.scrollIntoViewIfNeeded()
            await page.waitForTimeout(2500)  // dwell on VALID/INVALID status
          }

          // Close verify panel if there's a close button so the next caption renders cleanly
          const verifyClose = detail.locator('[data-testid="verify-close"]')
          if (await verifyClose.isVisible().catch(() => false)) {
            await verifyClose.click()
            await page.waitForTimeout(300)
          }
        }
      }

      // Brief settle before the next caption paints over this detail
      await page.waitForTimeout(800)

      // Buffer between scenarios for rate limiter (rate limit is disabled in compose, so short)
      if (i < SCENARIOS.length - 1) await page.waitForTimeout(2500)
    }

    await showTitleCard(page, 'Auditex', 'github.com/vsenthil7/auditex   |   DoraHacks BUIDL #43345   |   6 scenarios shown - all signed by Vertex consensus, 3 with Article 14 human oversight.', 4500)
  })
})
