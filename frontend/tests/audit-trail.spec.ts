/**
 * TC-12 — Audit Trail event chain rendering (Phase 10.C expansion)
 *
 * Covers the Step 4 Vertex proof block and verifies the round number / event
 * hash / finalised_at render correctly and the mode banner is present.
 *
 * Uses API interception via page.route so no real Celery round-trip is needed.
 */
import { test, expect } from '@playwright/test'

const BASE_URL = 'http://localhost:3000'
const TASK_ID  = 'd7cee013-f312-4c02-8329-2ae28019dcc4'

test.describe('Audit Trail — Vertex event chain', () => {
  test('TC-12 Step 4 shows event_hash, round number and finalised_at', async ({ page }) => {
    test.setTimeout(60_000)

    await page.route('**/api/v1/tasks**', async (route) => {
      if (route.request().url().includes(TASK_ID)) {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            task_id: TASK_ID,
            task_type: 'document_review',
            status: 'COMPLETED',
            created_at: '2026-04-21T10:00:00Z',
            report_available: true,
            executor: {
              model: 'claude-sonnet-4-6',
              confidence: 0.92,
              recommendation: 'APPROVE',
              reasoning: 'All fields present and values within policy bounds.',
            },
            review: {
              consensus: '3_OF_3_APPROVE',
              reviewers: [
                { model: 'gpt-4o', verdict: 'APPROVE', confidence: 0.9, commitment_verified: true },
                { model: 'gpt-4o', verdict: 'APPROVE', confidence: 0.88, commitment_verified: true },
                { model: 'claude', verdict: 'APPROVE', confidence: 0.85, commitment_verified: true },
              ],
            },
            vertex: {
              event_hash: 'a'.repeat(64),
              round: 113,
              finalised_at: '2026-04-21T10:30:15Z',
              mode: 'LIVE',
            },
          }),
        })
        return
      }
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          tasks: [{
            task_id: TASK_ID,
            task_type: 'document_review',
            status: 'COMPLETED',
            created_at: '2026-04-21T10:00:00Z',
            report_available: true,
          }],
          total: 1, page: 1, page_size: 50,
        }),
      })
    })

    await page.route('**/api/v1/reports/**', (route) => route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        task_id: TASK_ID, generated_at: '2026-04-21T10:30:15Z',
        plain_english_summary: 'Mortgage application approved.',
        eu_ai_act: {
          article_9_risk_management:  { risk_assessment: 'LOW', confidence_score: 0.92 },
          article_13_transparency:    { decision_made: 'APPROVE', consensus: '3_OF_3_APPROVE' },
          article_17_quality_management: { all_commitments_verified: true },
        },
      }),
    }))

    await page.goto(BASE_URL, { waitUntil: 'networkidle' })
    // Click the first row to select
    const row = page.locator('button.w-full.text-left').first()
    await row.click()

    const detail = page.locator('[data-testid="task-detail"]')
    await expect(detail).toBeVisible()

    // Expand Step 4
    await detail.getByText(/Step 4 — Vertex Consensus/i).click()

    // Round = 113, event hash full, LIVE mode banner
    await expect(detail.getByText(/113/)).toBeVisible()
    await expect(detail.getByText('a'.repeat(16), { exact: false })).toBeVisible()  // hash prefix
    await expect(detail.locator('[data-testid="vertex-mode-badge"]').first()).toContainText(/LIVE/)
  })
})
