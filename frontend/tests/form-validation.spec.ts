/**
 * TC-20 — Form Validation: SubmitTaskForm blocks empty / whitespace-only submits
 *
 * Verifies:
 *   - TC-20a: clicking Submit with empty document shows the validation error
 *   - TC-20b: whitespace-only document is still treated as empty (no backend call)
 *   - TC-20c: once a valid document is typed, error clears and POST fires
 */
import { test, expect } from '@playwright/test'

const BASE_URL = 'http://localhost:3000'

test.describe('Form Validation', () => {
  test('TC-20a empty document shows validation error + no POST fired', async ({ page }) => {
    test.setTimeout(30_000)

    let postCount = 0
    await page.route('**/api/v1/tasks?**', (route) => route.fulfill({
      status: 200, contentType: 'application/json',
      body: JSON.stringify({ tasks: [], total: 0, page: 1, page_size: 50 }),
    }))
    await page.route('**/api/v1/tasks', (route) => {
      if (route.request().method() === 'POST') postCount++
      route.fulfill({
        status: 200, contentType: 'application/json',
        body: JSON.stringify({ task_id: 'should-not-happen', status: 'QUEUED' }),
      })
    })

    await page.goto(BASE_URL, { waitUntil: 'networkidle' })
    await page.getByRole('button', { name: /Submit Task/i }).click()

    await expect(page.getByText(/Document content is required/i)).toBeVisible()
    expect(postCount).toBe(0)
  })

  test('TC-20b whitespace-only document is treated as empty', async ({ page }) => {
    test.setTimeout(30_000)

    let postCount = 0
    await page.route('**/api/v1/tasks?**', (route) => route.fulfill({
      status: 200, contentType: 'application/json',
      body: JSON.stringify({ tasks: [], total: 0, page: 1, page_size: 50 }),
    }))
    await page.route('**/api/v1/tasks', (route) => {
      if (route.request().method() === 'POST') postCount++
      route.fulfill({
        status: 200, contentType: 'application/json',
        body: JSON.stringify({ task_id: 'should-not-happen', status: 'QUEUED' }),
      })
    })

    await page.goto(BASE_URL, { waitUntil: 'networkidle' })
    await page.locator('textarea').fill('     \t  \n  ')
    await page.getByRole('button', { name: /Submit Task/i }).click()

    await expect(page.getByText(/Document content is required/i)).toBeVisible()
    expect(postCount).toBe(0)
  })

  test('TC-20c valid document fires POST and clears textarea', async ({ page }) => {
    test.setTimeout(30_000)

    let postPayload: any = null
    await page.route('**/api/v1/tasks?**', (route) => route.fulfill({
      status: 200, contentType: 'application/json',
      body: JSON.stringify({ tasks: [], total: 0, page: 1, page_size: 50 }),
    }))
    await page.route('**/api/v1/tasks', (route) => {
      if (route.request().method() === 'POST') {
        postPayload = JSON.parse(route.request().postData() ?? '{}')
      }
      route.fulfill({
        status: 200, contentType: 'application/json',
        body: JSON.stringify({
          task_id: 'validated-task-1', task_type: 'document_review',
          status: 'QUEUED', created_at: '2026-04-21T21:00:00Z', report_available: false,
        }),
      })
    })

    await page.goto(BASE_URL, { waitUntil: 'networkidle' })
    const textarea = page.locator('textarea')
    await textarea.fill('This is a valid document body for compliance review.')
    await page.getByRole('button', { name: /Submit Task/i }).click()

    // Wait for the POST to land
    await expect.poll(() => postPayload, { timeout: 5_000 }).not.toBeNull()
    expect(postPayload.task_type).toBe('document_review')
    expect(postPayload.payload.document).toContain('valid document body')

    // Textarea clears after successful submit
    await expect(textarea).toHaveValue('', { timeout: 5_000 })
  })
})
