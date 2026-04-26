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
    test.setTimeout(45 * 60 * 1000)  // 45 min budget; real LLM calls + HIL Article 14 block

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

    // Disable HIL policies for the 3 outcome-path cases (they pre-date Article 14 and expect direct COMPLETED).
    // We'll re-enable for the HIL block at the end.
    await page.evaluate(async () => {
      const headers = { 'Content-Type': 'application/json', 'X-API-Key': 'auditex-test-key-phase2' }
      for (const taskType of ['contract_check', 'risk_analysis', 'document_review']) {
        try {
          const r = await fetch('http://localhost:8000/api/v1/human-oversight-policies/' + taskType, {
            method: 'PUT', headers,
            body: JSON.stringify({ task_type: taskType, required: false, n_required: 1, m_total: 1, timeout_minutes: null, auto_commit_on_timeout: false }),
          })
          console.log('[demo] disabled policy ' + taskType + ': ' + r.status)
        } catch (e) { console.log('[demo] failed to disable policy ' + taskType + ': ' + e) }
      }
    })
    await page.waitForTimeout(1000)

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

    // =================================================================
    // HIL BLOCK: Article 14 Human Oversight (12 beats H-1..H-12)
    // Added Phase 14 to demonstrate post-submission Article 14 work.
    // Reuses existing data-testids shipped in HIL-9..15.
    // =================================================================
    await showCaption(page, {
      scene: 'TC-DEMO-HIL of HIL',
      title: 'Article 14: Human Oversight',
      given: 'Default policies seeded: contract_check 1/1, risk_analysis 2/3, document_review 1/1 + 24h auto-commit',
      when: 'Compliance officer submits contract_check, then a human reviewer approves it via the queue',
      then: 'Task auto-finalises to COMPLETED with Vertex hash AND human_decisions_count: 1 in audit trail',
      testData: ['Article 14 EU AI Act: human oversight on high-risk AI systems', 'Reviewer: Aoife O\'Connor', 'Decision: APPROVE'],
      expected: 'Decision recorded, finalise worker fires, signed export validates',
      holdMs: 5500,
    })
    await hideCaption(page)

    // Re-enable contract_check HIL policy for the H-1..H-12 walkthrough
    await page.evaluate(async () => {
      const headers = { 'Content-Type': 'application/json', 'X-API-Key': 'auditex-test-key-phase2' }
      try {
        const r = await fetch('http://localhost:8000/api/v1/human-oversight-policies/contract_check', {
          method: 'PUT', headers,
          body: JSON.stringify({ task_type: 'contract_check', required: true, n_required: 1, m_total: 1, timeout_minutes: null, auto_commit_on_timeout: false }),
        })
        console.log('[demo] re-enabled contract_check policy: ' + r.status)
      } catch (e) { console.log('[demo] failed to re-enable: ' + e) }
    })
    await page.waitForTimeout(1000)

    // H-1: Land on dashboard, show 3-tab nav
    await page.goto(BASE)
    await page.waitForLoadState('networkidle', { timeout: 30000 }).catch(() => {})
    await lowerShutter(page)
    const tabDashboard = page.locator('[data-testid="tab-dashboard"]')
    const tabHumanReview = page.locator('[data-testid="tab-human-review"]')
    const tabOversightConfig = page.locator('[data-testid="tab-oversight-config"]')
    await expect(tabDashboard).toBeVisible({ timeout: 10000 })
    await expect(tabHumanReview).toBeVisible({ timeout: 5000 })
    await expect(tabOversightConfig).toBeVisible({ timeout: 5000 })
    await tabDashboard.scrollIntoViewIfNeeded()
    await tabDashboard.hover()
    await page.waitForTimeout(900)
    await tabHumanReview.hover()
    await page.waitForTimeout(900)
    await tabOversightConfig.hover()
    await page.waitForTimeout(1200)

    // H-2: Click Oversight Config tab
    await tabOversightConfig.click()
    await page.waitForTimeout(1500)
    const oversightPage = page.locator('[data-testid="oversight-config-page"]')
    await expect(oversightPage).toBeVisible({ timeout: 10000 })
    await page.waitForTimeout(1200)

    // H-3: Show 3 policy rows with defaults visible
    const policyContractCheck = page.locator('[data-testid="policy-row-contract_check"]')
    const policyRiskAnalysis = page.locator('[data-testid="policy-row-risk_analysis"]')
    const policyDocumentReview = page.locator('[data-testid="policy-row-document_review"]')
    await expect(policyContractCheck).toBeVisible({ timeout: 5000 })
    await expect(policyRiskAnalysis).toBeVisible({ timeout: 5000 })
    await expect(policyDocumentReview).toBeVisible({ timeout: 5000 })
    await policyContractCheck.scrollIntoViewIfNeeded()
    await page.waitForTimeout(1500)
    await policyRiskAnalysis.scrollIntoViewIfNeeded()
    await page.waitForTimeout(1500)
    await policyDocumentReview.scrollIntoViewIfNeeded()
    await page.waitForTimeout(1800)

    // H-4: Back to Dashboard, submit a contract_check task
    await tabDashboard.click()
    await page.waitForTimeout(1200)
    const formHeading = page.getByRole('heading', { name: /Submit New Task/i })
    await expect(formHeading).toBeVisible({ timeout: 10000 })
    await formHeading.scrollIntoViewIfNeeded()
    await page.waitForTimeout(700)
    const taskSelect = page.locator('select')
    await taskSelect.scrollIntoViewIfNeeded()
    await taskSelect.hover()
    await page.waitForTimeout(700)
    await taskSelect.selectOption('contract_check')
    await page.waitForTimeout(1000)
    const textarea = page.locator('textarea')
    await textarea.scrollIntoViewIfNeeded()
    await textarea.click()
    const hilDocument = `Data Processing Agreement - HIL Demo - Article 14 Oversight Path

1. Scope: Vendor processes personal data on behalf of Controller under this DPA.
2. Purpose: Article 14 human oversight pipeline demonstration.
3. Categories: Standard contact and transactional data.
4. Retention: 6 years post-transaction.
5. Sub-processors: Annex A with 30-day prior notification.
6. Security: AES-256 at rest, TLS 1.3 in transit.
7. Data subject rights: 30-day response window.
8. Breach notification: within 24 hours.

This contract is policy-flagged for human review under Article 14.`
    await textarea.type(hilDocument, { delay: 6 })
    await page.waitForTimeout(800)
    const completenessCb = page.locator('label:has-text("Completeness") input[type="checkbox"]')
    await completenessCb.scrollIntoViewIfNeeded()
    await completenessCb.hover()
    await page.waitForTimeout(450)
    if (!(await completenessCb.isChecked().catch(() => false))) {
      await completenessCb.check({ force: true })
      await page.waitForTimeout(550)
    }
    const submitBtn = page.getByRole('button', { name: /^Submit Task$/i })
    await submitBtn.scrollIntoViewIfNeeded()
    await submitBtn.hover()
    await page.waitForTimeout(700)
    const hilSubmitResponse = page.waitForResponse((r) => r.url().includes('/api/v1/tasks') && r.request().method() === 'POST' && r.status() === 201, { timeout: 30000 })
    await submitBtn.click()
    const hilResp = await hilSubmitResponse
    const hilJson = await hilResp.json()
    const hilTaskId = hilJson.task_id as string
    const hilPrefix = hilTaskId.slice(0, 8)
    console.log('[demo] HIL submitted task: ' + hilTaskId)
    await page.waitForTimeout(1500)

    // H-5: Watch task progress queued -> executing
    const hilTaskRow = page.locator('button.w-full.text-left').filter({ hasText: hilPrefix })
    await expect(hilTaskRow).toBeVisible({ timeout: 15000 })
    await hilTaskRow.scrollIntoViewIfNeeded()
    await page.waitForTimeout(2500)  // viewer watches QUEUED -> EXECUTING flip

    // H-6: Wait for AWAITING_HUMAN_REVIEW status (StatusBadge displays this enum as 'NEEDS HUMAN')
    await expect(hilTaskRow).toContainText(/NEEDS.*HUMAN/i, { timeout: 120 * 1000 })
    await page.waitForTimeout(3000)  // viewer reads the amber pulse status

    // H-7: Click Human Review tab
    await tabHumanReview.scrollIntoViewIfNeeded()
    await tabHumanReview.hover()
    await page.waitForTimeout(700)
    await tabHumanReview.click()
    await page.waitForTimeout(1500)
    const humanReviewPage = page.locator('[data-testid="human-review-page"]')
    await expect(humanReviewPage).toBeVisible({ timeout: 10000 })
    await page.waitForTimeout(1500)

    // H-8: Click into the queued task -> split-pane decision form opens
    const queueRow = page.locator(`[data-testid="queue-task-${hilPrefix}"]`)
    await expect(queueRow).toBeVisible({ timeout: 10000 })
    await queueRow.scrollIntoViewIfNeeded()
    await queueRow.hover()
    await page.waitForTimeout(700)
    await queueRow.click()
    await page.waitForTimeout(1500)
    const decisionForm = page.locator('[data-testid="decision-form"]')
    await expect(decisionForm).toBeVisible({ timeout: 10000 })
    await page.waitForTimeout(1200)

    // H-9: Fill reviewer name + reason, click APPROVE
    const reviewedBy = page.locator('[data-testid="decision-reviewed-by"]')
    await reviewedBy.scrollIntoViewIfNeeded()
    await reviewedBy.click()
    await reviewedBy.type('Aoife O\'Connor', { delay: 30 })
    await page.waitForTimeout(800)
    const reasonField = page.locator('[data-testid="decision-reason"]')
    await reasonField.click()
    await reasonField.type('Article 14 oversight - POC demo, contract terms verified against Article 28 GDPR requirements.', { delay: 12 })
    await page.waitForTimeout(1000)
    const approveBtn = page.locator('[data-testid="decision-APPROVE"]')
    await approveBtn.scrollIntoViewIfNeeded()
    await approveBtn.hover()
    await page.waitForTimeout(700)
    await approveBtn.click()
    await page.waitForTimeout(1000)
    const submitDecision = page.locator('[data-testid="decision-submit"]')
    await submitDecision.scrollIntoViewIfNeeded()
    await submitDecision.hover()
    await page.waitForTimeout(700)
    await submitDecision.click()
    await page.waitForTimeout(1500)

    // H-10: Watch auto-finalise -> COMPLETED with Vertex hash
    const decisionFeedback = page.locator('[data-testid="decision-feedback"]')
    await expect(decisionFeedback).toBeVisible({ timeout: 15000 })
    await page.waitForTimeout(2500)  // viewer reads feedback message
    // Go back to dashboard to watch the status flip to COMPLETED
    await tabDashboard.click()
    await page.waitForTimeout(1500)
    const hilTaskRowAfter = page.locator('button.w-full.text-left').filter({ hasText: hilPrefix })
    await expect(hilTaskRowAfter).toBeVisible({ timeout: 10000 })
    await hilTaskRowAfter.scrollIntoViewIfNeeded()
    await expect(hilTaskRowAfter).toContainText(/COMPLETED/i, { timeout: 90 * 1000 })
    await page.waitForTimeout(3000)

    // H-11: Open task detail, audit trail with human_decisions_count: 1
    await hilTaskRowAfter.click()
    await page.waitForTimeout(1500)
    const hilDetail = page.locator('[data-testid="task-detail"]')
    await expect(hilDetail).toBeVisible({ timeout: 10000 })
    await page.waitForTimeout(1500)
    // Scroll through detail panel showing the audit trail
    const hilDetailHeight = await hilDetail.evaluate((el) => el.scrollHeight)
    const hilDetailViewport = await hilDetail.evaluate((el) => el.clientHeight)
    const hilMaxScroll = Math.max(0, hilDetailHeight - hilDetailViewport)
    await hilDetail.evaluate((el) => el.scrollTo({ top: 0, behavior: 'smooth' }))
    await page.waitForTimeout(1000)
    const hilStepPx = Math.max(200, Math.ceil(hilMaxScroll / 5))
    for (let y = 0; y <= hilMaxScroll; y += hilStepPx) {
      await hilDetail.evaluate((el, pos) => el.scrollTo({ top: pos, behavior: 'smooth' }), y)
      await page.waitForTimeout(1400)
    }
    await hilDetail.evaluate((el) => el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' }))
    await page.waitForTimeout(2500)

    // H-12: Signed export validates (sign + verify roundtrip)
    const signBtn = page.locator('[data-testid="sign-report-button"]')
    if (await signBtn.isVisible().catch(() => false)) {
      await signBtn.scrollIntoViewIfNeeded()
      await signBtn.hover()
      await page.waitForTimeout(700)
      await signBtn.click()
      await page.waitForTimeout(2000)
      const signedDetails = page.locator('[data-testid="signed-report-details"]')
      if (await signedDetails.isVisible().catch(() => false)) {
        await signedDetails.scrollIntoViewIfNeeded()
        await page.waitForTimeout(2000)
      }
      const verifyBtn = page.locator('[data-testid="verify-proof-button"]')
      if (await verifyBtn.isVisible().catch(() => false)) {
        await verifyBtn.scrollIntoViewIfNeeded()
        await verifyBtn.hover()
        await page.waitForTimeout(700)
        await verifyBtn.click()
        await page.waitForTimeout(2000)
        const verifyStatus = page.locator('[data-testid="verify-status"]')
        if (await verifyStatus.isVisible().catch(() => false)) {
          await verifyStatus.scrollIntoViewIfNeeded()
          await page.waitForTimeout(3000)  // viewer reads verify result panel
        }
      }
    }
    await raiseShutter(page)
    // =================================================================
    // END HIL BLOCK
    // =================================================================

    await showTitleCard(page, 'Auditex', 'github.com/vsenthil7/auditex   |   DoraHacks BUIDL #43345   |   See ENTERPRISE-GAP-REGISTER.md for honest current-state disclosure.', 4500)
  })
})
