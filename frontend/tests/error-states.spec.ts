/**
 * TC-16 — Error States: FAILED + ESCALATED UI rendering
 */
import { test, expect } from '@playwright/test'

const BASE_URL = 'http://localhost:3000'

test.describe('Error States', () => {
  test('TC-16a FAILED task shows red lifecycle + failure banner', async ({ page }) => {
    test.setTimeout(60_000)
    const TASK_ID = 'failed-1234-aaaa-bbbb-cccc-dddddddddddd'

    await page.route('**/api/v1/tasks**', async (route) => {
      const url = route.request().url()
      if (url.includes(TASK_ID)) {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({
          task_id: TASK_ID, task_type: 'document_review', status: 'FAILED',
          created_at: '2026-04-21T10:00:00Z', report_available: false,
          error_message: 'Claude API timeout after 3 retries',
        })})
        return
      }
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({
        tasks: [{ task_id: TASK_ID, task_type: 'document_review', status: 'FAILED', created_at: '2026-04-21T10:00:00Z', report_available: false }],
        total: 1, page: 1, page_size: 50,
      })})
    })

    await page.goto(BASE_URL, { waitUntil: 'networkidle' })
    await page.locator('button.w-full.text-left').first().click()
    const detail = page.locator('[data-testid="task-detail"]')
    await expect(detail).toBeVisible()
    await expect(detail.getByText(/Task Failed/i)).toBeVisible()
    await expect(detail.getByText(/Claude API timeout/i)).toBeVisible()
    // Red dot in the lifecycle timeline
    expect(await detail.locator('.bg-red-500.border-red-500').count()).toBeGreaterThan(0)
  })

  test('TC-16b ESCALATED task uses default failure copy when no error_message', async ({ page }) => {
    test.setTimeout(60_000)
    const TASK_ID = 'escalated-a-bbbb-cccc-dddd-eeeeeeeeeeee'

    await page.route('**/api/v1/tasks**', async (route) => {
      const url = route.request().url()
      if (url.includes(TASK_ID)) {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({
          task_id: TASK_ID, task_type: 'risk_analysis', status: 'ESCALATED',
          created_at: '2026-04-21T10:00:00Z', report_available: false,
        })})
        return
      }
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({
        tasks: [{ task_id: TASK_ID, task_type: 'risk_analysis', status: 'ESCALATED', created_at: '2026-04-21T10:00:00Z', report_available: false }],
        total: 1, page: 1, page_size: 50,
      })})
    })

    await page.goto(BASE_URL, { waitUntil: 'networkidle' })
    await page.locator('button.w-full.text-left').first().click()
    const detail = page.locator('[data-testid="task-detail"]')
    await expect(detail).toBeVisible()
    await expect(detail.getByText(/Task did not complete successfully/i)).toBeVisible()
    await expect(detail.getByText(/ESCALATED/i).first()).toBeVisible()
  })
})
