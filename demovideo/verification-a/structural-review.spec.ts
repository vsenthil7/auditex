/**
 * Auditex demo structural review (Option A).
 * Re-runs the same flow as end-to-end-demo.spec.ts but with hard assertions per scene.
 * If any scene gate fails, the report tells you exactly which scene broke.
 * No video frame inspection - this is a logic-level review.
 */
import { test, expect, Page, APIRequestContext } from '@playwright/test'

const BASE = 'http://localhost:3000'
const API = 'http://localhost:8000'
const API_KEY = 'auditex-test-key-phase2'

interface Scene {
  id: string
  taskType: string
  document: string
  criteria: string[]
}

const SCENES: Scene[] = [
  { id: 'TC-A-1', taskType: 'contract_check', document: 'DPA covering Article 28 GDPR for review.', criteria: ['Completeness'] },
  { id: 'TC-A-2', taskType: 'risk_analysis', document: 'Loan: GBP 12M unsecured, 6mo term, no docs.', criteria: ['Risk Assessment'] },
  { id: 'TC-A-3', taskType: 'document_review', document: 'Employment letter for Jane Smith - salary blank.', criteria: ['Employment Verification'] },
]

test.describe('Demo structural review (Option A)', () => {
  for (const sc of SCENES) {
    test(`scene ${sc.id}: ${sc.taskType} renders all gates`, async ({ page }) => {
      test.setTimeout(180_000)

      // Gate 1: dashboard reachable
      await page.goto(BASE)
      await expect(page.getByRole('heading', { name: /Submit New Task/i })).toBeVisible({ timeout: 10000 })
      await expect(page.locator('select')).toBeVisible()
      await expect(page.locator('textarea')).toBeVisible()

      // Gate 2: form accepts the inputs
      await page.locator('select').selectOption(sc.taskType)
      await page.locator('textarea').fill(sc.document)
      for (const label of sc.criteria) {
        const cb = page.locator(`label:has-text("${label}") input[type="checkbox"]`)
        await cb.check({ force: true })
        await expect(cb).toBeChecked()
      }

      // Gate 3: POST returns 201 with task_id
      const respPromise = page.waitForResponse(r => r.url().includes('/api/v1/tasks') && r.request().method() === 'POST' && r.status() === 201, { timeout: 30000 })
      await page.getByRole('button', { name: /^Submit Task$/i }).click()
      const resp = await respPromise
      const newTaskId = (await resp.json()).task_id as string
      expect(newTaskId).toMatch(/^[0-9a-f-]{36}$/)

      // Gate 4: task appears in the list and reaches COMPLETED
      const idPrefix = newTaskId.slice(0, 8)
      const row = page.locator('button.w-full.text-left').filter({ hasText: idPrefix })
      await expect(row).toBeVisible({ timeout: 15000 })
      await row.click()
      await expect(row).toContainText(/COMPLETED/i, { timeout: 90_000 })

      // Gate 5: detail panel renders all 5 pipeline steps
      const detail = page.locator('[data-testid="task-detail"]')
      await expect(detail).toBeVisible({ timeout: 15000 })
      for (let n = 1; n <= 5; n++) {
        await expect(detail.locator(`text=/Step ${n}/i`).first()).toBeVisible({ timeout: 30000 })
      }

      // Gate 6: executor block has model + recommendation populated
      await expect(detail.locator('text=/STEP 2/i').first()).toBeVisible()
      const stepTwoSection = detail.locator('text=/Model/i').first()
      await expect(stepTwoSection).toBeVisible({ timeout: 30000 })

      // Gate 7: review panel shows 3 reviewers
      const reviewerRows = detail.locator('text=/Reviewer\\\\s+[123]/i')
      await expect(reviewerRows).toHaveCount(3, { timeout: 30000 })

      // Gate 8: vertex consensus event hash present
      await expect(detail.locator('text=/Vertex.*LIVE|Event Hash/i').first()).toBeVisible({ timeout: 30000 })
    })
  }
})
