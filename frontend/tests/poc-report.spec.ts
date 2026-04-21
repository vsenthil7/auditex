/**
 * TC-14 — PoC Report: all three EU AI Act article sections render
 */
import { test, expect } from '@playwright/test'

const BASE_URL = 'http://localhost:3000'
const TASK_ID  = '65a1d0eb-cb11-4c88-a1e8-dbdce048efea'

test.describe('PoC Report — EU AI Act sections', () => {
  test('TC-14 Article 9, Article 13, Article 17 all render with status', async ({ page }) => {
    test.setTimeout(60_000)

    await page.route('**/api/v1/tasks**', async (route) => {
      const url = route.request().url()
      if (url.includes(TASK_ID)) {
        await route.fulfill({
          status: 200, contentType: 'application/json',
          body: JSON.stringify({
            task_id: TASK_ID, task_type: 'risk_analysis', status: 'COMPLETED',
            created_at: '2026-04-21T10:00:00Z', report_available: true,
            executor: { model: 'claude', confidence: 0.85, recommendation: 'APPROVE' },
            review: { consensus: '3_OF_3_APPROVE', reviewers: [] },
            vertex: { event_hash: 'c'.repeat(64), round: 50, finalised_at: '2026-04-21T10:15:00Z', mode: 'LIVE' },
          }),
        })
        return
      }
      await route.fulfill({
        status: 200, contentType: 'application/json',
        body: JSON.stringify({
          tasks: [{
            task_id: TASK_ID, task_type: 'risk_analysis', status: 'COMPLETED',
            created_at: '2026-04-21T10:00:00Z', report_available: true,
          }],
          total: 1, page: 1, page_size: 50,
        }),
      })
    })

    await page.route('**/api/v1/reports/**', (route) => route.fulfill({
      status: 200, contentType: 'application/json',
      body: JSON.stringify({
        task_id: TASK_ID, generated_at: '2026-04-21T10:15:00Z',
        plain_english_summary: 'Low-risk business. Approved.',
        eu_ai_act: {
          article_9_risk_management:     { risk_assessment: 'LOW', confidence_score: 0.85 },
          article_13_transparency:       { decision_made: 'APPROVE', consensus: '3_OF_3_APPROVE' },
          article_17_quality_management: { all_commitments_verified: true },
        },
      }),
    }))

    await page.goto(BASE_URL, { waitUntil: 'networkidle' })
    await page.locator('button.w-full.text-left').first().click()
    const detail = page.locator('[data-testid="task-detail"]')
    await expect(detail).toBeVisible()

    // The PoC report summary renders
    await expect(detail.locator('[data-testid="plain-english-summary"]')).toContainText('Low-risk business')

    // EU AI Act accordion — all 3 article headers
    const compliance = detail.locator('[data-testid="eu-ai-act-compliance"]')
    await expect(compliance).toBeVisible()
    await expect(compliance.getByText(/Article 9 — Risk Management/i)).toBeVisible()
    await expect(compliance.getByText(/Article 13 — Transparency/i)).toBeVisible()
    await expect(compliance.getByText(/Article 17 — Quality Management/i)).toBeVisible()

    // All three show COMPLIANT status badge
    const compliantBadges = compliance.locator('span').filter({ hasText: /^COMPLIANT$/ })
    expect(await compliantBadges.count()).toBeGreaterThanOrEqual(3)
  })
})
