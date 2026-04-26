/**
 * Auditex end-to-end captioned demo - 6-scenario matrix with Oversight Config visibility.
 * 3 task types x 2 paths each (no-HIL direct + HIL via human) = 6 scenarios.
 *
 * Each scenario:
 *   1. (For first scenario) shutter stays up until title card paints - no app flicker
 *   2. Caption (GIVEN/WHEN/THEN/EXPECTED)
 *   3. Visit Oversight Config tab so viewer sees policy state for the upcoming task type
 *   4. Back to Dashboard, fill form, submit
 *   5. Watch through HIL queue if applicable
 *   6. Detail panel: expand all 5 pipeline steps, dwell on Step 5 with Articles expanded
 *   7. Vertex sign + verify (the show-runner)
 *   8. (HIL only) Export EU AI Act JSON to show human_decisions in signed bundle
 *
 * Run: cd frontend; npx playwright test tests/demo/end-to-end-demo.spec.ts --headed --project=chromium
 */
import { test, expect } from '@playwright/test'
import { showCaption, hideCaption, showTitleCard } from './caption-overlay'

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
    given: 'A clean DPA covering Article 28 GDPR. Policy: NO human required.',
    when: 'Compliance officer submits for contract_check',
    then: '3 reviewers reach BFT consensus APPROVE, signed Vertex event recorded',
    expected: 'COMPLETED with executor + reviewers + Vertex hash + signed report VALID',
    taskType: 'contract_check',
    criteria: ['Completeness'],
    hil: false,
    document: `Data Processing Agreement - TechCorp Ltd & Vendor Services Inc.

1. Scope: Vendor processes personal data on behalf of TechCorp under this DPA.
2. Purpose: Payment processing for e-commerce transactions (Art. 28 GDPR).
3. Categories: Customer name, email, billing address, order history.
4. Retention: 6 years post-transaction.
5. Sub-processors: Annex A, with 30-day prior notification.
6. Security: AES-256 at rest, TLS 1.3 in transit, SOC 2 Type II.
7. Data subject rights: 30-day response window.
8. Breach notification: within 24 hours.

DPA is complete, all Article 28 items addressed.`,
  },
  {
    scene: 'TC-2 of 6',
    title: 'Contract Check - Human APPROVE (Article 14)',
    given: 'Same task type, but policy now: human REQUIRED before finalisation',
    when: 'Submit, then reviewer approves via Human Review queue',
    then: 'Task pauses at NEEDS HUMAN, human approves, finalises with human signature',
    expected: 'COMPLETED with human_decisions: 1, signed Vertex event includes reviewer',
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
    given: 'High-risk loan with impossible income + no docs. Policy: NO human.',
    when: 'Submit for risk_analysis',
    then: '3 reviewers detect anomaly + vote REJECT',
    expected: 'COMPLETED REJECT with red flag reasoning + signed Vertex event VALID',
    taskType: 'risk_analysis',
    criteria: ['Income Verification', 'Risk Assessment'],
    hil: false,
    document: `Loan Application - Applicant ID 88472

Stated annual income: GBP 4,500,000
Stated employer: TechCorp Ltd (entry-level role, started 2 weeks ago)
Loan amount requested: GBP 12,000,000 unsecured
Term: 6 months bullet repayment
Stated assets: cryptocurrency holdings (no exchange records)
Stated purpose: investment in private offshore venture
Provided documentation: 1 page CV, no payslips, no bank statements
Credit history: no record found in UK credit reference agencies`,
  },
  {
    scene: 'TC-4 of 6',
    title: 'Risk Analysis - Human OVERRIDES (Article 14)',
    given: 'A clean-looking loan AI would APPROVE - but Risk Committee policy requires human',
    when: 'Submit, AI consensus is APPROVE, then senior reviewer REJECTS based on policy',
    then: 'Human REJECT decision OVERRIDES AI consensus - shows the point of Article 14',
    expected: 'COMPLETED with human REJECT, AI APPROVE preserved in audit, Vertex VALID',
    taskType: 'risk_analysis',
    criteria: ['Risk Assessment'],
    hil: true,
    hilDecision: 'REJECT',
    document: `Loan Application - Applicant ID 91241

Stated annual income: GBP 95,000 (verified, payslips attached)
Stated employer: Reputable PLC (8-year tenure, senior role)
Loan amount: GBP 250,000 secured against family home
Term: 25 years amortising
Documentation: 2yr accounts, 6mo bank statements, payslips, ID
Credit history: clean, score 825/999, 3 prior loans repaid in full
Purpose: home extension and renovation

Standard prime borrower, low default risk.`,
  },
  {
    scene: 'TC-5 of 6',
    title: 'Document Review - Auto REQUEST_AMENDMENTS',
    given: 'Almost-complete employment verification missing one key field',
    when: 'Submit for document_review (no human required)',
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

Salary field is blank. Verifier must request this before approval.`,
  },
  {
    scene: 'TC-6 of 6',
    title: 'Document Review - Human REQUEST_AMENDMENTS (Article 14)',
    given: 'Document review with HIL policy enabled - human reviewer requests fixes',
    when: 'Submit, then reviewer manually requests amendments',
    then: 'Task pauses, then finalises with human REQUEST_AMENDMENTS signature',
    expected: 'COMPLETED with human REQUEST_AMENDMENTS, Vertex VALID',
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

Reviewer to flag missing fields manually under Article 14.`,
  },
]

async function setPolicy(request: any, taskType: string, required: boolean) {
  await request.put(`${API}/api/v1/human-oversight-policies/${taskType}`, {
    headers: { 'X-API-Key': API_KEY, 'Content-Type': 'application/json' },
    data: { task_type: taskType, required, n_required: 1, m_total: 1, timeout_minutes: null, auto_commit_on_timeout: false },
  })
}

test.describe('Auditex 6-Scenario Captioned Demo with Oversight Config', () => {
  test('3 task types x 2 paths (no-HIL + HIL) - shows policy state + Vertex sign+verify', async ({ page, request }) => {
    test.setTimeout(60 * 60 * 1000)

    // Inject a black shutter that stays up until we explicitly lower it.
    // Prevents app flicker during navigation/caption transitions.
    await page.addInitScript(() => {
      const id = 'demo-shutter'
      if (document.getElementById(id)) return
      const s = document.createElement('div')
      s.id = id
      s.style.cssText = 'position:fixed;inset:0;z-index:2147483646;background:#0f172a;transition:opacity 0.2s ease;opacity:1;pointer-events:auto;'
      const body = document.body || document.documentElement
      if (body) body.appendChild(s)
      else document.addEventListener('DOMContentLoaded', () => document.body.appendChild(s))
    })

    async function lowerShutter() {
      await page.evaluate(() => {
        const s = document.getElementById('demo-shutter') as HTMLElement | null
        if (s) { s.style.opacity = '0'; setTimeout(() => { s.style.pointerEvents = 'none' }, 200) }
      })
      await page.waitForTimeout(220)
    }

    // Initial nav - shutter is up so app paints behind it invisibly
    await page.goto(BASE)
    await page.waitForLoadState('networkidle', { timeout: 30000 }).catch(() => {})
    await page.waitForTimeout(300)

    // Title card paints over the shutter immediately (caption overlay z-index higher than shutter)
    await showTitleCard(page, 'Auditex', 'EU AI Act compliance audit pipeline. 6 scenarios: 3 task types x (Auto + Human-in-Loop). Tamper-proof Vertex consensus on every event. DoraHacks BUIDL #43345.', 4000)

    // Now lower the shutter for first scenario (caption will paint immediately after this)
    await lowerShutter()

    for (let i = 0; i < SCENARIOS.length; i++) {
      const sc = SCENARIOS[i]

      // Pre-set policy state for this scenario
      await setPolicy(request, sc.taskType, sc.hil)
      await page.waitForTimeout(250)

      // Caption paints directly over previous detail (or shutter for first scenario)
      await showCaption(page, {
        scene: sc.scene,
        title: sc.title,
        given: sc.given,
        when: sc.when,
        then: sc.then,
        testData: ['Task type: ' + sc.taskType, 'HIL: ' + (sc.hil ? 'ENABLED (' + sc.hilDecision + ')' : 'disabled'), 'Criteria: ' + sc.criteria.join(', ')],
        expected: sc.expected,
        holdMs: 3000,
      })
      await hideCaption(page)

      // === Oversight Config visit BEFORE submit, so viewer sees the policy state ===
      const tabOversight = page.locator('[data-testid="tab-oversight-config"]')
      if (await tabOversight.isVisible().catch(() => false)) {
        await tabOversight.scrollIntoViewIfNeeded()
        await tabOversight.click()
        await page.waitForTimeout(600)
        const policyRow = page.locator(`[data-testid="policy-row-${sc.taskType}"]`)
        if (await policyRow.isVisible().catch(() => false)) {
          await policyRow.scrollIntoViewIfNeeded()
          // Highlight the row briefly so viewer's eye goes there
          await policyRow.evaluate((el: HTMLElement) => {
            el.style.transition = 'background-color 0.3s'
            el.style.backgroundColor = '#fde68a'
            setTimeout(() => { el.style.backgroundColor = '' }, 2000)
          })
          await page.waitForTimeout(2200)  // viewer reads required: ON/OFF
        }
        // Back to dashboard for submission
        const tabDash = page.locator('[data-testid="tab-dashboard"]')
        await tabDash.click()
        await page.waitForTimeout(400)
      }

      // === Form fill ===
      const formHeading = page.getByRole('heading', { name: /Submit New Task/i })
      await formHeading.scrollIntoViewIfNeeded()
      await page.waitForTimeout(200)
      const taskSelect = page.locator('select')
      await taskSelect.scrollIntoViewIfNeeded()
      await taskSelect.selectOption(sc.taskType)
      await page.waitForTimeout(300)

      const textarea = page.locator('textarea')
      await textarea.scrollIntoViewIfNeeded()
      await textarea.click()
      await page.keyboard.press('Control+A')
      await page.keyboard.press('Delete')
      await textarea.type(sc.document, { delay: 2 })
      await page.waitForTimeout(200)

      for (const label of sc.criteria) {
        const cb = page.locator(`label:has-text("${label}") input[type="checkbox"]`)
        await cb.scrollIntoViewIfNeeded()
        if (!(await cb.isChecked().catch(() => false))) {
          await cb.check({ force: true })
          await page.waitForTimeout(150)
        }
      }
      await page.waitForTimeout(200)

      const submitBtn = page.getByRole('button', { name: /^Submit Task$/i })
      await submitBtn.scrollIntoViewIfNeeded()
      const submitResponse = page.waitForResponse((r) => r.url().includes('/api/v1/tasks') && r.request().method() === 'POST' && r.status() === 201, { timeout: 30000 })
      await submitBtn.click()
      const resp = await submitResponse
      const respJson = await resp.json()
      const newTaskId = respJson.task_id as string
      const idPrefix = newTaskId.slice(0, 8)
      console.log('[demo] ' + sc.scene + ' submitted: ' + newTaskId + ' (' + sc.taskType + ', hil=' + sc.hil + ')')
      await page.waitForTimeout(500)

      const myTaskRow = page.locator('button.w-full.text-left').filter({ hasText: idPrefix })
      await expect(myTaskRow).toBeVisible({ timeout: 15000 })
      await myTaskRow.scrollIntoViewIfNeeded()
      await page.waitForTimeout(300)

      if (sc.hil) {
        // HIL path
        await myTaskRow.click()
        await page.waitForTimeout(500)
        await expect(myTaskRow).toContainText(/NEEDS.*HUMAN/i, { timeout: 120 * 1000 })
        await page.waitForTimeout(1500)

        const tabHumanReview = page.locator('[data-testid="tab-human-review"]')
        await tabHumanReview.click()
        await page.waitForTimeout(500)

        const queueRow = page.locator(`[data-testid="queue-task-${idPrefix}"]`)
        await expect(queueRow).toBeVisible({ timeout: 10000 })
        await queueRow.click()
        await page.waitForTimeout(500)

        const reviewedBy = page.locator('[data-testid="decision-reviewed-by"]')
        await reviewedBy.click()
        await reviewedBy.type('Aoife O\'Connor', { delay: 12 })
        await page.waitForTimeout(250)
        const reasonField = page.locator('[data-testid="decision-reason"]')
        await reasonField.click()
        const reasonText =
          sc.hilDecision === 'APPROVE' ? 'Article 14 oversight - terms verified, approved.'
          : sc.hilDecision === 'REJECT' ? 'Article 14 oversight - policy override; loan amount over committee threshold without senior sign-off.'
          : 'Article 14 oversight - amendments needed before approval.'
        await reasonField.type(reasonText, { delay: 5 })
        await page.waitForTimeout(300)

        const decisionBtn = page.locator(`[data-testid="decision-${sc.hilDecision}"]`)
        await decisionBtn.scrollIntoViewIfNeeded()
        await decisionBtn.click()
        await page.waitForTimeout(250)

        const submitDecision = page.locator('[data-testid="decision-submit"]')
        await submitDecision.scrollIntoViewIfNeeded()
        await submitDecision.click()
        await page.waitForTimeout(500)

        const decisionFeedback = page.locator('[data-testid="decision-feedback"]')
        await expect(decisionFeedback).toBeVisible({ timeout: 15000 })
        await page.waitForTimeout(1000)

        const tabDashboard = page.locator('[data-testid="tab-dashboard"]')
        await tabDashboard.click()
        await page.waitForTimeout(500)
      }

      // Wait for COMPLETED
      const myRowAfter = page.locator('button.w-full.text-left').filter({ hasText: idPrefix })
      await expect(myRowAfter).toBeVisible({ timeout: 10000 })
      await myRowAfter.scrollIntoViewIfNeeded()
      await expect(myRowAfter).toContainText(/COMPLETED/i, { timeout: 120 * 1000 })
      await myRowAfter.click()
      await page.waitForTimeout(500)

      // Detail panel
      const detail = page.locator('[data-testid="task-detail"]')
      await expect(detail).toBeVisible({ timeout: 10000 })
      await expect(detail.locator('text=/Step 2/i').first()).toBeVisible({ timeout: 30000 })
      await page.waitForTimeout(500)

      // Expand all 5 step accordions
      const steps = detail.locator('button', { hasText: /^Step [1-5]/ })
      const stepCount = await steps.count()
      for (let s = 0; s < Math.min(stepCount, 5); s++) {
        await steps.nth(s).scrollIntoViewIfNeeded()
        await steps.nth(s).click()
        await page.waitForTimeout(150)
      }

      // Scroll back to top of detail panel, then slow-scroll all the way through so all 5 steps are visible in sequence
      await detail.evaluate((el) => el.scrollTo({ top: 0, behavior: 'instant' as ScrollBehavior }))
      await page.waitForTimeout(800)
      const detailHeight = await detail.evaluate((el) => el.scrollHeight)
      const detailViewport = await detail.evaluate((el) => el.clientHeight)
      const maxScroll = Math.max(0, detailHeight - detailViewport)
      const stepReadTimes = [1200, 2200, 1800, 1500, 2500]
      for (let s = 0; s < Math.min(stepCount, 5); s++) {
        await steps.nth(s).scrollIntoViewIfNeeded()
        await page.waitForTimeout(stepReadTimes[s] || 1500)
      }

      // Step 5 final pose: scroll to bottom and dwell on the report
      await detail.evaluate((el) => el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' }))
      await page.waitForTimeout(1500)

      // Step 5: ensure compliance report is expanded; expand each Article 9/13/17 dropdown if collapsed
      if (stepCount >= 5) {
        const stepFive = steps.nth(4)
        await stepFive.scrollIntoViewIfNeeded()
        const reportContent = detail.locator('[data-testid="eu-ai-act-compliance"]')
        if (!(await reportContent.isVisible().catch(() => false))) {
          await stepFive.click()
          await page.waitForTimeout(400)
        }
        // Expand each Article (the chevron buttons next to "COMPLIANT")
        const articleHeaders = detail.locator('text=/Article (9|13|17)/i')
        const artCount = await articleHeaders.count()
        for (let a = 0; a < artCount; a++) {
          const hdr = articleHeaders.nth(a)
          await hdr.scrollIntoViewIfNeeded().catch(() => {})
          await hdr.click({ force: true }).catch(() => {})
          await page.waitForTimeout(300)
        }
        await page.waitForTimeout(2000)  // dwell on expanded articles
      }

      // Vertex sign + verify
      const signBtn = detail.locator('[data-testid="sign-report-button"]')
      if (await signBtn.isVisible().catch(() => false)) {
        await signBtn.scrollIntoViewIfNeeded()
        await page.waitForTimeout(300)
        await signBtn.click()
        await page.waitForTimeout(1500)

        const signedDetails = detail.locator('[data-testid="signed-report-details"]')
        if (await signedDetails.isVisible().catch(() => false)) {
          await signedDetails.scrollIntoViewIfNeeded()
          await page.waitForTimeout(1200)
        }

        const verifyBtn = detail.locator('[data-testid="verify-proof-button"]')
        if (await verifyBtn.isVisible().catch(() => false)) {
          await verifyBtn.scrollIntoViewIfNeeded()
          await page.waitForTimeout(300)
          await verifyBtn.click()
          await page.waitForTimeout(1500)

          const verifyResultPanel = detail.locator('[data-testid="verify-result-panel"]')
          if (await verifyResultPanel.isVisible().catch(() => false)) {
            await verifyResultPanel.scrollIntoViewIfNeeded()
            await page.waitForTimeout(2200)  // dwell on VALID/INVALID
          }

          const verifyClose = detail.locator('[data-testid="verify-close"]')
          if (await verifyClose.isVisible().catch(() => false)) {
            await verifyClose.click()
            await page.waitForTimeout(250)
          }
        }
      }

      // For HIL scenarios: click Export EU AI Act JSON briefly to flash human_decisions visible
      if (sc.hil) {
        const exportBtn = detail.locator('text=/Export EU AI Act JSON/i').first()
        if (await exportBtn.isVisible().catch(() => false)) {
          await exportBtn.scrollIntoViewIfNeeded()
          await page.waitForTimeout(800)
          // Don't actually click (would trigger download); just dwell on the visible button
        }
        const downloadBundle = detail.locator('[data-testid="download-signed-bundle"]')
        if (await downloadBundle.isVisible().catch(() => false)) {
          await downloadBundle.scrollIntoViewIfNeeded()
          await page.waitForTimeout(800)
        }
      }

      await page.waitForTimeout(500)

      if (i < SCENARIOS.length - 1) await page.waitForTimeout(1500)
    }

    await showTitleCard(page, 'Auditex', 'github.com/vsenthil7/auditex   |   DoraHacks BUIDL #43345   |   6 scenarios shown - all signed by Vertex consensus, 3 with Article 14 human oversight.', 4000)
  })
})
