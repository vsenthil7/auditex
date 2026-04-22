/**
 * TC-14 -- SignReportButton + VerifySignatureDialog (Phase 12 Step 3a)
 *
 * Verifies: completed task shows Sign button; signing renders panel;
 * downloading fires .json; Verify button shows 3 green checks.
 */
import { test, expect } from '@playwright/test'

const BASE_URL = 'http://localhost:3000'
const TASK_ID  = '9b970bed-4d94-4d8b-931e-6f9f8a59e5d8'

test.describe('Signed Export -- Sign + Verify', () => {
  test('TC-14 full flow: Sign + Verify renders correctly', async ({ page }) => {
    test.setTimeout(60_000)

    await page.route('**/api/v1/tasks**', async (route) => {
      const url = route.request().url()
      if (url.includes(TASK_ID) && !url.includes('/export')) {
        await route.fulfill({
          status: 200, contentType: 'application/json',
          body: JSON.stringify({
            task_id: TASK_ID, task_type: 'contract_check', status: 'COMPLETED',
            created_at: '2026-04-21T10:00:00Z', report_available: true,
            executor: { model: 'claude', confidence: 0.91, recommendation: 'APPROVE' },
            review: {
              consensus: '3_OF_3_APPROVE',
              reviewers: [
                { model: 'gpt-4o', verdict: 'APPROVE', confidence: 0.9, commitment_verified: true },
                { model: 'gpt-4o', verdict: 'APPROVE', confidence: 0.9, commitment_verified: true },
                { model: 'claude', verdict: 'APPROVE', confidence: 0.9, commitment_verified: true },
              ],
            },
            vertex: {
              event_hash: 'b'.repeat(64), round: 42,
              finalised_at: '2026-04-21T10:20:00Z', mode: 'LIVE',
            },
          }),
        })
        return
      }
      await route.fulfill({
        status: 200, contentType: 'application/json',
        body: JSON.stringify({
          tasks: [{
            task_id: TASK_ID, task_type: 'contract_check', status: 'COMPLETED',
            created_at: '2026-04-21T10:00:00Z', report_available: true,
          }],
          total: 1, page: 1, page_size: 50,
        }),
      })
    })

    await page.route(`**/api/v1/reports/${TASK_ID}`, (route) => route.fulfill({
      status: 200, contentType: 'application/json',
      body: JSON.stringify({
        task_id: TASK_ID, generated_at: '2026-04-21T10:20:00Z',
        plain_english_summary: 'Contract is compliant.',
        eu_ai_act: {
          article_9_risk_management:     { risk_assessment: 'LOW', confidence_score: 0.91 },
          article_13_transparency:       { decision_made: 'APPROVE', consensus: '3_OF_3_APPROVE' },
          article_17_quality_management: { all_commitments_verified: true },
        },
      }),
    }))

    await page.route(`**/api/v1/reports/${TASK_ID}/sign`, (route) => route.fulfill({
      status: 200, contentType: 'application/json',
      body: JSON.stringify({
        payload: { task_id: TASK_ID, compliant: true },
        signature: {
          algorithm: 'HMAC-SHA256',
          signing_key_id: 'kid-test-2026',
          signed_at: '2026-04-22T06:00:00Z',
          signature_hex: 'deadbeef'.repeat(8),
        },
        persisted: true,
      }),
    }))

    await page.route(`**/api/v1/events/${TASK_ID}/verify`, (route) => route.fulfill({
      status: 200, contentType: 'application/json',
      body: JSON.stringify({
        task_id: TASK_ID,
        verified: true,
        expected_hash: 'b'.repeat(64),
        computed_hash: 'b'.repeat(64),
        event_count: 7,
        reason: null,
        checks: [
          { name: 'has_expected_hash', ok: true },
          { name: 'has_events', ok: true },
          { name: 'chain_hash_matches', ok: true },
        ],
      }),
    }))

    await page.goto(BASE_URL, { waitUntil: 'networkidle' })
    await page.locator('button.w-full.text-left').first().click()
    const detail = page.locator('[data-testid=\"task-detail\"]')
    await expect(detail).toBeVisible()

    // Sign button
    const signBtn = detail.locator('[data-testid=\"sign-report-button\"]')
    await expect(signBtn).toBeVisible()

    const downloadPromise = page.waitForEvent('download')
    await signBtn.click()
    const panel = detail.locator('[data-testid=\"signed-report-details\"]')
    await expect(panel).toBeVisible()
    await expect(detail.locator('[data-testid=\"sig-algorithm\"]')).toContainText('HMAC-SHA256')
    await expect(detail.locator('[data-testid=\"sig-key-id\"]')).toContainText('kid-test-2026')
    await expect(detail.locator('[data-testid=\"sig-hex\"]')).toContainText('deadbeef')

    await detail.locator('[data-testid=\"download-signed-bundle\"]').click()
    const download = await downloadPromise
    expect(download.suggestedFilename()).toMatch(new RegExp(`auditex-report-${TASK_ID}-signed\\.json`))

    // Verify button
    const verifyBtn = detail.locator('[data-testid=\"verify-proof-button\"]')
    await expect(verifyBtn).toBeVisible()
    await verifyBtn.click()
    const result = detail.locator('[data-testid=\"verify-result-panel\"]')
    await expect(result).toBeVisible()
    await expect(detail.locator('[data-testid=\"verify-status\"]')).toContainText('Proof verified')
    await expect(detail.locator('[data-testid=\"check-has_expected_hash\"]')).toContainText('\u2713')
    await expect(detail.locator('[data-testid=\"check-has_events\"]')).toContainText('\u2713')
    await expect(detail.locator('[data-testid=\"check-chain_hash_matches\"]')).toContainText('\u2713')
    await expect(detail.locator('[data-testid=\"verify-event-count\"]')).toContainText('7')
  })
})
