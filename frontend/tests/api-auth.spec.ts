/**
 * TC-17 — API Authentication: backend 401 on missing / invalid X-API-Key
 *
 * Hits the real backend directly (not through the UI) to prove auth middleware works.
 */
import { test, expect } from '@playwright/test'

const API_URL = 'http://localhost:8000'

test.describe('API Authentication', () => {
  test('TC-17a missing X-API-Key → 401', async ({ request }) => {
    test.setTimeout(30_000)
    const res = await request.post(`${API_URL}/api/v1/tasks`, {
      data: { task_type: 'document_review', payload: { document: 'x', review_criteria: [] } },
      failOnStatusCode: false,
    })
    expect(res.status()).toBe(401)
  })

  test('TC-17b invalid X-API-Key → 401', async ({ request }) => {
    test.setTimeout(30_000)
    const res = await request.post(`${API_URL}/api/v1/tasks`, {
      headers: { 'X-API-Key': 'totally-wrong-key' },
      data: { task_type: 'document_review', payload: { document: 'x', review_criteria: [] } },
      failOnStatusCode: false,
    })
    expect(res.status()).toBe(401)
  })

  test('TC-17c valid X-API-Key → NOT 401', async ({ request }) => {
    test.setTimeout(30_000)
    const res = await request.get(`${API_URL}/api/v1/tasks?page=1&page_size=1`, {
      headers: { 'X-API-Key': 'auditex-test-key-phase2' },
      failOnStatusCode: false,
    })
    // May be 200 or 500 (DB state dependent) but must NOT be 401
    expect(res.status()).not.toBe(401)
  })
})
