/**
 * Auditex - HIL-15: end-to-end Playwright spec for the Human Review pages.
 * Exercises the 3-tab UI (Dashboard / Human Review / Oversight Config) against the real backend.
 * Real submission to /api/v1/tasks - real backend triggers worker gate - real human decision via UI.
 */
import { test, expect, request } from '@playwright/test'

const BASE = 'http://localhost:3000'
const API = 'http://localhost:8000'
const API_KEY = 'auditex-test-key-phase2'

test.describe('HIL-15 Human Review E2E (Article 14)', () => {
  test.setTimeout(180_000)

  test('tab nav renders all three pages', async ({ page }) => {
    await page.goto(BASE)
    await expect(page.getByTestId('tab-dashboard')).toBeVisible()
    await expect(page.getByTestId('tab-human-review')).toBeVisible()
    await expect(page.getByTestId('tab-oversight-config')).toBeVisible()

    await page.getByTestId('tab-human-review').click()
    await expect(page.getByTestId('human-review-page')).toBeVisible({ timeout: 8000 })

    await page.getByTestId('tab-oversight-config').click()
    await expect(page.getByTestId('oversight-config-page')).toBeVisible({ timeout: 8000 })

    // Three policy rows seeded by migration 0005
    await expect(page.getByTestId('policy-row-contract_check')).toBeVisible()
    await expect(page.getByTestId('policy-row-risk_analysis')).toBeVisible()
    await expect(page.getByTestId('policy-row-document_review')).toBeVisible()
  })

  test('oversight config page can edit + save a policy round-trip', async ({ page }) => {
    await page.goto(BASE)
    await page.getByTestId('tab-oversight-config').click()
    await expect(page.getByTestId('oversight-config-page')).toBeVisible()

    // Edit risk_analysis: bump M from 3 to 4 (does not violate quorum constraint)
    const mInput = page.getByTestId('m-total-risk_analysis')
    await mInput.fill('4')

    const saveBtn = page.getByTestId('save-policy-risk_analysis')
    await expect(saveBtn).toBeEnabled()
    await saveBtn.click()

    // Save returns - row should no longer be dirty (button reads Saved + disabled)
    await expect(saveBtn).toBeDisabled({ timeout: 5000 })

    // Reload the page entirely; the change must persist server-side
    await page.reload()
    await page.getByTestId('tab-oversight-config').click()
    await expect(page.getByTestId('m-total-risk_analysis')).toHaveValue('4')

    // Restore: M back to 3 so this test is idempotent
    await page.getByTestId('m-total-risk_analysis').fill('3')
    await page.getByTestId('save-policy-risk_analysis').click()
    await expect(page.getByTestId('save-policy-risk_analysis')).toBeDisabled()
  })

  test('full Article 14 flow: submit task -> AWAITING_HUMAN_REVIEW -> APPROVE via UI -> COMPLETED', async ({ page }) => {
    // Submit a real task via API (faster than UI form, isolates this test from form bugs)
    const apiCtx = await request.newContext({ extraHTTPHeaders: { 'X-API-Key': API_KEY } })
    const submitResp = await apiCtx.post(`${API}/api/v1/tasks`, {
      data: {
        task_type: 'contract_check',
        payload: {
          document: 'HIL-15 E2E test - DPA Article 28 GDPR coverage check.',
          review_criteria: ['completeness'],
          agent_id: 'ede4995c-4129-4066-8d96-fa8e246a4a10'
        }
      }
    })
    expect(submitResp.status()).toBe(201)
    const submitJson = await submitResp.json()
    const taskId = submitJson.task_id as string
    const idPrefix = taskId.slice(0, 8)

    // Wait for backend to flow Submit -> Execute -> Review -> AWAITING_HUMAN_REVIEW (~12-20s)
    await page.goto(BASE)
    await page.getByTestId('tab-human-review').click()
    await expect(page.getByTestId('human-review-page')).toBeVisible()

    // Queue auto-refreshes every 5s. Wait for our task to appear (max 60s).
    const myRow = page.locator(`[data-testid="queue-task-${idPrefix}"]`)
    await expect(myRow).toBeVisible({ timeout: 60_000 })

    // Click into our task
    await myRow.click()
    await expect(page.getByTestId('decision-form')).toBeVisible({ timeout: 5000 })

    // Fill reviewer + reason, click APPROVE
    await page.getByTestId('decision-reviewed-by').fill('hil15@e2e.local')
    await page.getByTestId('decision-reason').fill('E2E test approval - DPA looks complete.')
    await page.getByTestId('decision-APPROVE').click()
    await page.waitForTimeout(300)  // let React register the decision selection

    // Click submit and wait for the actual API call to settle
    const submitPromise = page.waitForResponse((r) => r.url().includes('/human-decision') && r.request().method() === 'POST', { timeout: 30000 })
    await page.getByTestId('decision-submit').click()
    const decisionResp = await submitPromise
    expect(decisionResp.status()).toBe(200)

    // After submit, the queued task disappears from the visible queue (moved to FINALISING/COMPLETED)
    // This is the most reliable post-submit signal - feedback is too transient to assert against
    await expect(myRow).not.toBeVisible({ timeout: 15000 })

    // Verify backend: task should now be COMPLETED (HIL-8 Celery worker finalises)
    await page.waitForTimeout(8000)
    const detailResp = await apiCtx.get(`${API}/api/v1/tasks/${taskId}`)
    expect(detailResp.status()).toBe(200)
    const detail = await detailResp.json()
    expect(['COMPLETED', 'FINALISING']).toContain(detail.status)  // FINALISING during the brief Vertex window

    // Within 60s it must reach COMPLETED
    let finalStatus = detail.status
    for (let i = 0; i < 30 && finalStatus !== 'COMPLETED'; i++) {
      await page.waitForTimeout(2000)
      const r = await apiCtx.get(`${API}/api/v1/tasks/${taskId}`)
      finalStatus = (await r.json()).status
    }
    expect(finalStatus).toBe('COMPLETED')
    await apiCtx.dispose()
  })
})
