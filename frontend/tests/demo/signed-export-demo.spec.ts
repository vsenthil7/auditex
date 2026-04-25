/**
 * Auditex captioned demo walkthrough for DoraHacks BUIDL #43345.
 * Each scene: caption (test case + GWT + test data + expected) -> UI action.
 * Watchable without audio.
 *
 * Run: cd frontend; npx playwright test tests/demo/signed-export-demo.spec.ts --headed --project=chromium
 * Out: frontend/test-results/.../video.webm
 */
import { test, expect } from '@playwright/test'
import { showCaption, hideCaption, showTitleCard, ACTION_PAUSE } from './caption-overlay'

const BASE = 'http://localhost:3000'

const TASK_APPROVE = { task_id: 'a1111111-1111-1111-1111-111111111111', task_type: 'contract_check', recommendation: 'APPROVE' }
const TASK_REJECT  = { task_id: 'b2222222-2222-2222-2222-222222222222', task_type: 'risk_analysis',  recommendation: 'REJECT' }
const TASK_REQUEST = { task_id: 'c3333333-3333-3333-3333-333333333333', task_type: 'document_review', recommendation: 'REQUEST_AMENDMENTS' }
const TASKS = [TASK_APPROVE, TASK_REJECT, TASK_REQUEST]

function buildTaskDetail(t: typeof TASK_APPROVE) {
  return {
    task_id: t.task_id,
    task_type: t.task_type,
    status: 'COMPLETED',
    created_at: '2026-04-22T10:00:00Z',
    report_available: true,
    executor: { model: 'claude-sonnet-4', confidence: 0.91, recommendation: t.recommendation, reasoning: 'Executor verdict: ' + t.recommendation },
    review: {
      consensus: '3_OF_3_' + t.recommendation,
      reviewers: [
        { model: 'gpt-4o', verdict: t.recommendation, confidence: 0.92, commitment_verified: true, commitment: '0xa1b2c3d4e5f6' },
        { model: 'gpt-4o', verdict: t.recommendation, confidence: 0.89, commitment_verified: true, commitment: '0xf6e5d4c3b2a1' },
        { model: 'claude-sonnet-4', verdict: t.recommendation, confidence: 0.94, commitment_verified: true, commitment: '0xabcdef123456' },
      ],
    },
    vertex: { event_hash: 'b'.repeat(64), round: 42, finalised_at: '2026-04-22T10:20:00Z', mode: 'LIVE' },
  }
}

test.describe('Auditex Captioned Demo', () => {
  test('DoraHacks submission walkthrough', async ({ page }) => {
    test.setTimeout(600_000)

    await page.route('**/api/v1/tasks**', async (route) => {
      const url = route.request().url()
      for (const t of TASKS) {
        if (url.includes(t.task_id) && !url.includes('/export')) {
          await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(buildTaskDetail(t)) })
          return
        }
      }
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({
        tasks: TASKS.map(t => ({ task_id: t.task_id, task_type: t.task_type, status: 'COMPLETED', created_at: '2026-04-22T10:00:00Z', report_available: true })),
        total: TASKS.length, page: 1, page_size: 50
      })})
    })
    await page.route('**/api/v1/reports/*/sign', async (r) => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ algorithm: 'HMAC-SHA256', key_id: 'kid-2026-04', signature_hex: 'deadbeef' + '0'.repeat(56), signed_at: '2026-04-22T10:25:00Z' }) }))
    await page.route('**/api/v1/reports/*/export*', async (r) => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ task_id: TASK_APPROVE.task_id, articles: { '9': { covered: true }, '13': { covered: true }, '17': { covered: true } }, summary: 'DPA covers Article 28.' }) }))
    await page.route('**/api/v1/events/*/verify', async (r) => r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ verified: true, expected_hash: 'b'.repeat(64), computed_hash: 'b'.repeat(64), event_count: 7, checks: [{ name: 'has_expected_hash', ok: true }, { name: 'has_events', ok: true }, { name: 'chain_hash_matches', ok: true }] }) }))

    // INTRO
    await page.goto(BASE)
    await page.waitForTimeout(1000)
    await showTitleCard(page, 'Auditex', 'Cryptographically-verifiable audit trails for every AI decision. DoraHacks BUIDL #43345 - Track 3 Agent Economy.', 4000)

    // SCENE 1
    await showCaption(page, {
      scene: 'TC-DEMO-1',
      title: 'Dashboard Overview',
      given: 'Compliance officer opens the Auditex dashboard',
      when: 'The tasks list loads from /api/v1/tasks',
      then: 'All audit tasks render with status, type, and timestamp',
      testData: ['3 completed tasks across contract_check, risk_analysis, document_review'],
      expected: 'Tasks list visible, each tappable for detail view',
    })
    await hideCaption(page)
    await page.mouse.move(220, 130); await page.waitForTimeout(600)
    await page.mouse.move(700, 130); await page.waitForTimeout(600)
    await page.mouse.move(420, 400); await page.waitForTimeout(600)
    await page.evaluate(() => window.scrollTo({ top: 300, behavior: 'smooth' })); await page.waitForTimeout(1200)
    await page.evaluate(() => window.scrollTo({ top: 0, behavior: 'smooth' })); await page.waitForTimeout(1200)

    // SCENE 2
    await showCaption(page, {
      scene: 'TC-DEMO-2',
      title: 'Open APPROVE Task Detail',
      given: 'A completed contract_check audit with consensus APPROVE',
      when: 'User clicks the task row in the list',
      then: 'Task detail panel renders with the 5-stage pipeline',
      testData: ['Task ID: a1111111-...', 'Executor: claude-sonnet-4 (confidence 0.91)', 'Reviewers: 3/3 APPROVE'],
      expected: 'Task detail visible with executor + reviewers + vertex hash',
    })
    await hideCaption(page)
    await page.locator('button.w-full.text-left').nth(0).click()
    await page.waitForTimeout(ACTION_PAUSE)
    const detail = page.locator('[data-testid="task-detail"]')
    await expect(detail).toBeVisible()
    for (let y = 0; y <= 1000; y += 200) {
      await detail.evaluate((el, pos) => el.scrollTo({ top: pos, behavior: 'smooth' }), y)
      await page.waitForTimeout(900)
    }
    await detail.evaluate((el) => el.scrollTo({ top: 0, behavior: 'smooth' }))
    await page.waitForTimeout(800)

    // SCENE 3
    await showCaption(page, {
      scene: 'TC-DEMO-3',
      title: 'Expand All 5 Pipeline Steps',
      given: 'Task detail shows 5 collapsed pipeline stages',
      when: 'User expands each: Submit -> Execute -> Review -> Vertex -> Report',
      then: 'Each step reveals reasoning, commitments, timings, and verdicts',
      testData: ['Step 1: Submission (Redis queue)', 'Step 2: AI Executor (claude-sonnet-4)', 'Step 3: Review Panel (3 reviewers, BFT consensus)', 'Step 4: Vertex Consensus (event hash + round 42)', 'Step 5: Compliance Report (Articles 9 / 13 / 17)'],
      expected: 'All 5 panels open showing full audit trail',
    })
    await hideCaption(page)
    const steps = detail.locator('button', { hasText: /^Step [1-5]/ })
    const stepCount = await steps.count()
    for (let i = 0; i < Math.min(stepCount, 5); i++) {
      await steps.nth(i).scrollIntoViewIfNeeded()
      await page.waitForTimeout(400)
      await steps.nth(i).click()
      await page.waitForTimeout(1000)
    }
    for (let y = 0; y <= 1800; y += 300) {
      await detail.evaluate((el, pos) => el.scrollTo({ top: pos, behavior: 'smooth' }), y)
      await page.waitForTimeout(800)
    }

    // SCENE 4
    await showCaption(page, {
      scene: 'TC-DEMO-4',
      title: 'Sign Report + Download Bundle',
      given: 'Completed audit with Vertex-finalised event chain',
      when: 'User clicks Sign this report, then Download signed bundle',
      then: 'HMAC-SHA256 signature renders + JSON file downloads',
      testData: ['Algorithm: HMAC-SHA256', 'Key ID: kid-2026-04', 'Filename: auditex-report-{taskId}-signed.json'],
      expected: 'Signature panel + downloaded .json with HMAC verifiable offline',
    })
    await hideCaption(page)
    const signBtn = detail.locator('[data-testid="sign-report-button"]')
    await signBtn.scrollIntoViewIfNeeded(); await page.waitForTimeout(600)
    await signBtn.hover(); await page.waitForTimeout(400)
    await signBtn.click(); await page.waitForTimeout(1800)
    const dlPromise = page.waitForEvent('download')
    await detail.locator('[data-testid="download-signed-bundle"]').hover(); await page.waitForTimeout(400)
    await detail.locator('[data-testid="download-signed-bundle"]').click()
    const dl = await dlPromise
    expect(dl.suggestedFilename()).toMatch(new RegExp('auditex-report-.*-signed\.json'))
    await page.waitForTimeout(1200)

    // SCENE 5
    await showCaption(page, {
      scene: 'TC-DEMO-5',
      title: 'Verify Vertex Proof (third-party trustless)',
      given: 'Signed bundle with claimed vertex_event_hash',
      when: 'Verifier hits GET /api/v1/events/{task_id}/verify',
      then: 'Server recomputes the chain hash and returns 3 green checks',
      testData: ['Check 1: has_expected_hash', 'Check 2: has_events (7 events in chain)', 'Check 3: chain_hash_matches'],
      expected: 'All three checks pass with green ticks - audit is genuine',
    })
    await hideCaption(page)
    const verifyBtn = detail.locator('[data-testid="verify-proof-button"]')
    await verifyBtn.scrollIntoViewIfNeeded(); await page.waitForTimeout(600)
    await verifyBtn.hover(); await page.waitForTimeout(400)
    await verifyBtn.click(); await page.waitForTimeout(2000)
    await expect(detail.locator('[data-testid="check-has_expected_hash"]')).toContainText('✓')
    await expect(detail.locator('[data-testid="check-has_events"]')).toContainText('✓')
    await expect(detail.locator('[data-testid="check-chain_hash_matches"]')).toContainText('✓')
    await page.waitForTimeout(2500)

    // CLOSING
    await showTitleCard(page, 'Auditex', 'github.com/vsenthil7/auditex   |   DoraHacks BUIDL #43345   |   See ENTERPRISE-GAP-REGISTER.md for honest current-state disclosure.', 4500)
  })
})

