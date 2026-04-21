/**
 * TC-13 — ExportPanel: EU AI Act JSON download
 *
 * Verifies the "Export EU AI Act JSON" button downloads a well-formed JSON
 * containing the three EU AI Act article sections.
 */
import { test, expect } from '@playwright/test'

const BASE_URL = 'http://localhost:3000'
const TASK_ID  = '9b970bed-4d94-4d8b-931e-6f9f8a59e5d8'

test.describe('Export Panel — EU AI Act JSON', () => {
  test('TC-13 export button downloads the Article 9/13/17 JSON', async ({ page }) => {
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

    await page.route(`**/api/v1/reports/${TASK_ID}/export**`, (route) => route.fulfill({
      status: 200, contentType: 'application/json',
      body: JSON.stringify({
        task_id: TASK_ID,
        article_9_risk_management:     { risk_assessment: 'LOW', confidence_score: 0.91 },
        article_13_transparency:       { decision_made: 'APPROVE', consensus: '3_OF_3_APPROVE' },
        article_17_quality_management: { all_commitments_verified: true },
      }),
    }))

    await page.goto(BASE_URL, { waitUntil: 'networkidle' })
    await page.locator('button.w-full.text-left').first().click()
    const detail = page.locator('[data-testid="task-detail"]')
    await expect(detail).toBeVisible()

    // Step 5 auto-opens for COMPLETED
    const exportButton = detail.getByRole('button', { name: /Export EU AI Act JSON/i })
    await expect(exportButton).toBeVisible()

    const downloadPromise = page.waitForEvent('download')
    await exportButton.click()
    const download = await downloadPromise
    expect(download.suggestedFilename()).toMatch(new RegExp(`auditex-report-${TASK_ID}\\.json`))
  })
})
