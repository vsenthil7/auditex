/**
 * TC-15 — Vertex Mode Badge: LIVE vs STUB rendering
 */
import { test, expect } from '@playwright/test'

const BASE_URL = 'http://localhost:3000'

test.describe('Vertex Mode Badge', () => {
  test('TC-15a LIVE badge rendered for mode=LIVE task', async ({ page }) => {
    test.setTimeout(60_000)
    const TASK_ID = 'live-task-aaaa-bbbb-cccc-dddddddddddd'

    await page.route('**/api/v1/tasks**', async (route) => {
      const url = route.request().url()
      if (url.includes(TASK_ID)) {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({
          task_id: TASK_ID, task_type: 'document_review', status: 'COMPLETED',
          created_at: '2026-04-21T10:00:00Z', report_available: false,
          vertex: { event_hash: 'a'.repeat(64), round: 113, finalised_at: '2026-04-21T10:30:00Z', mode: 'LIVE' },
        })})
        return
      }
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({
        tasks: [{ task_id: TASK_ID, task_type: 'document_review', status: 'COMPLETED', created_at: '2026-04-21T10:00:00Z', report_available: false }],
        total: 1, page: 1, page_size: 50,
      })})
    })

    await page.goto(BASE_URL, { waitUntil: 'networkidle' })
    await page.locator('button.w-full.text-left').first().click()
    const detail = page.locator('[data-testid="task-detail"]')
    await expect(detail).toBeVisible()

    // LIVE badge in header
    const headerBadge = detail.locator('[data-testid="vertex-mode-badge"]').first()
    await expect(headerBadge).toContainText(/LIVE/)
    await expect(headerBadge).toContainText(/FoxMQ BFT/)

    // Step 4 expanded → second LIVE badge inside the proof section
    await detail.getByText(/Step 4 — Vertex Consensus/i).click()
    const badges = detail.locator('[data-testid="vertex-mode-badge"]')
    expect(await badges.count()).toBeGreaterThanOrEqual(2)
  })

  test('TC-15b STUB badge rendered when mode is absent', async ({ page }) => {
    test.setTimeout(60_000)
    const TASK_ID = 'stub-task-aaaa-bbbb-cccc-dddddddddddd'

    await page.route('**/api/v1/tasks**', async (route) => {
      const url = route.request().url()
      if (url.includes(TASK_ID)) {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({
          task_id: TASK_ID, task_type: 'document_review', status: 'COMPLETED',
          created_at: '2026-04-21T10:00:00Z', report_available: false,
          vertex: { event_hash: 'z'.repeat(64), round: 1, finalised_at: '2026-04-21T10:30:00Z' },  // no mode
        })})
        return
      }
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({
        tasks: [{ task_id: TASK_ID, task_type: 'document_review', status: 'COMPLETED', created_at: '2026-04-21T10:00:00Z', report_available: false }],
        total: 1, page: 1, page_size: 50,
      })})
    })

    await page.goto(BASE_URL, { waitUntil: 'networkidle' })
    await page.locator('button.w-full.text-left').first().click()
    const detail = page.locator('[data-testid="task-detail"]')
    await expect(detail).toBeVisible()

    const badge = detail.locator('[data-testid="vertex-mode-badge"]').first()
    await expect(badge).toContainText(/STUB/)
    await expect(badge).toContainText(/Redis counter/)
  })
})
