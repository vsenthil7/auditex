/**
 * TC-18 — Polling: 3-second refresh
 *
 * Counts API hits to /api/v1/tasks over an 8-second window. Polling should
 * fire ~3 times (initial + 2 ticks at 3s intervals).
 */
import { test, expect } from '@playwright/test'

const BASE_URL = 'http://localhost:3000'

test.describe('Polling', () => {
  test('TC-18 dashboard fires listTasks roughly every 3 seconds', async ({ page }) => {
    test.setTimeout(30_000)

    let hits = 0
    await page.route('**/api/v1/tasks?**', (route) => {
      hits++
      route.fulfill({
        status: 200, contentType: 'application/json',
        body: JSON.stringify({ tasks: [], total: 0, page: 1, page_size: 50 }),
      })
    })

    await page.goto(BASE_URL, { waitUntil: 'networkidle' })
    // Wait 8 seconds: initial + 2 tick intervals
    await page.waitForTimeout(8_000)

    // Expect at least 3 hits (initial + 2 ticks); allow up to 5 for timing slack
    expect(hits).toBeGreaterThanOrEqual(3)
    expect(hits).toBeLessThanOrEqual(5)
  })
})
