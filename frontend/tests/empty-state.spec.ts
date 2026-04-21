/**
 * TC-19 — Empty State: zero tasks on dashboard
 *
 * Mocks an empty task list and verifies:
 *   - "No tasks yet" message is shown
 *   - SubmitTaskForm is still visible (user can add tasks)
 *   - TaskDetail placeholder ("Select a task to view details") is shown
 */
import { test, expect } from '@playwright/test'

const BASE_URL = 'http://localhost:3000'

test.describe('Empty State', () => {
  test('TC-19 zero-tasks dashboard shows placeholder copy + submit form still usable', async ({ page }) => {
    test.setTimeout(30_000)

    await page.route('**/api/v1/tasks?**', (route) => route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ tasks: [], total: 0, page: 1, page_size: 50 }),
    }))

    await page.goto(BASE_URL, { waitUntil: 'networkidle' })

    // Task list shows the empty copy
    await expect(page.getByText(/No tasks yet/i)).toBeVisible()
    await expect(page.getByText(/Submit one above/i)).toBeVisible()

    // Submit form is still rendered
    await expect(page.getByRole('heading', { name: /Submit New Task/i })).toBeVisible()
    await expect(page.locator('textarea')).toBeVisible()
    await expect(page.getByRole('button', { name: /Submit Task/i })).toBeVisible()

    // Task detail placeholder copy is visible
    await expect(page.getByText(/Select a task to view details/i)).toBeVisible()
  })
})
