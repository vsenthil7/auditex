/**
 * Tests for src/services/api.ts
 * Covers: submitTask, getTask, listTasks, getReport, exportReport, transformReport edge cases.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'

const BASE_URL = 'http://localhost:8000'

// Helper — install a fetch mock returning the given response
function installFetch(responses: Array<{ ok: boolean; status?: number; body: unknown; text?: string }>) {
  const queue = [...responses]
  const fetchMock = vi.fn(async () => {
    const next = queue.shift()!
    return {
      ok: next.ok,
      status: next.status ?? (next.ok ? 200 : 500),
      json: async () => next.body,
      text: async () => next.text ?? JSON.stringify(next.body),
    } as unknown as Response
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

describe('api.submitTask', () => {
  beforeEach(() => vi.unstubAllGlobals())

  it('POSTs with wrapped payload + API key header', async () => {
    const fetchMock = installFetch([{ ok: true, body: { task_id: 't1' } }])
    const { submitTask } = await import('../services/api')

    const task = await submitTask({
      task_type: 'document_review',
      document: 'Lorem ipsum',
      review_criteria: ['completeness'],
    })

    expect(task).toEqual({ task_id: 't1' })
    expect(fetchMock).toHaveBeenCalledWith(
      `${BASE_URL}/api/v1/tasks`,
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({
          'Content-Type': 'application/json',
          'X-API-Key': expect.any(String),
        }),
      }),
    )
    const body = JSON.parse((fetchMock.mock.calls[0][1] as RequestInit).body as string)
    expect(body.task_type).toBe('document_review')
    expect(body.payload.document).toBe('Lorem ipsum')
    expect(body.payload.review_criteria).toEqual(['completeness'])
    expect(body.payload.agent_id).toBe('ede4995c-4129-4066-8d96-fa8e246a4a10')
  })

  it('throws on non-2xx response', async () => {
    installFetch([{ ok: false, status: 401, body: null, text: 'unauthorised' }])
    const { submitTask } = await import('../services/api')
    await expect(
      submitTask({ task_type: 'x', document: 'y', review_criteria: [] }),
    ).rejects.toThrow(/API 401/)
  })
})

describe('api.getTask', () => {
  beforeEach(() => vi.unstubAllGlobals())

  it('GETs /api/v1/tasks/:id', async () => {
    const fetchMock = installFetch([
      { ok: true, body: { task_id: 'abc', status: 'COMPLETED' } },
    ])
    const { getTask } = await import('../services/api')
    const t = await getTask('abc')
    expect(t.task_id).toBe('abc')
    expect(fetchMock.mock.calls[0][0]).toBe(`${BASE_URL}/api/v1/tasks/abc`)
  })
})

describe('api.listTasks', () => {
  beforeEach(() => vi.unstubAllGlobals())

  it('uses defaults page=1 size=50', async () => {
    const fetchMock = installFetch([
      { ok: true, body: { tasks: [], total: 0, page: 1, page_size: 50 } },
    ])
    const { listTasks } = await import('../services/api')
    await listTasks()
    expect(fetchMock.mock.calls[0][0]).toBe(`${BASE_URL}/api/v1/tasks?page=1&page_size=50`)
  })

  it('honours custom page + size', async () => {
    const fetchMock = installFetch([
      { ok: true, body: { tasks: [], total: 0, page: 3, page_size: 7 } },
    ])
    const { listTasks } = await import('../services/api')
    await listTasks(3, 7)
    expect(fetchMock.mock.calls[0][0]).toBe(`${BASE_URL}/api/v1/tasks?page=3&page_size=7`)
  })
})

describe('api.getReport + transformReport', () => {
  beforeEach(() => vi.unstubAllGlobals())

  it('maps eu_ai_act keys to articles with COMPLIANT/NON_COMPLIANT/PARTIAL status', async () => {
    installFetch([{
      ok: true,
      body: {
        task_id: 't1',
        generated_at: '2026-04-21T10:00:00Z',
        plain_english_summary: 'All good.',
        eu_ai_act: {
          article_9_risk_management:  { risk_assessment: 'LOW', confidence_score: 0.92 },
          article_13_transparency:    {
            consensus: '3_OF_3_APPROVE', decision_made: 'APPROVE',
            reviewers: [
              { model: 'gpt-4o',  verdict: 'APPROVE', confidence: 0.9 },
              { model: 'claude',  verdict: 'APPROVE', confidence: 0.85 },
            ],
          },
          article_17_quality_management: { all_commitments_verified: true },
        },
      },
    }])
    const { getReport } = await import('../services/api')
    const r = await getReport('t1')
    expect(r.task_id).toBe('t1')
    expect(r.plain_english_summary).toBe('All good.')
    expect(r.overall_recommendation).toBe('APPROVE')
    expect(r.confidence_score).toBe(0.92)

    const byArticle = Object.fromEntries(
      r.eu_ai_act_compliance.map(a => [a.article, a]),
    )
    expect(byArticle['Article 9'].status).toBe('COMPLIANT')
    expect(byArticle['Article 9'].findings.some(f => f.startsWith('risk assessment:'))).toBe(true)

    expect(byArticle['Article 13'].status).toBe('COMPLIANT')
    // Reviewers appear as findings with percentage
    expect(byArticle['Article 13'].findings.some(f => f.includes('gpt-4o'))).toBe(true)
    expect(byArticle['Article 13'].findings.some(f => f.includes('90%'))).toBe(true)

    expect(byArticle['Article 17'].status).toBe('COMPLIANT')
  })

  it('HIGH risk → NON_COMPLIANT, MEDIUM → PARTIAL, no consensus → PARTIAL, unverified → PARTIAL', async () => {
    installFetch([{
      ok: true,
      body: {
        task_id: 't2',
        plain_english_summary: '',
        generated_at: '',
        eu_ai_act: {
          article_9_risk_management:     { risk_assessment: 'HIGH' },
          article_13_transparency:       { },                        // no consensus
          article_17_quality_management: { all_commitments_verified: false },
        },
      },
    }])
    const { getReport } = await import('../services/api')
    const r = await getReport('t2')
    const byArticle = Object.fromEntries(r.eu_ai_act_compliance.map(a => [a.article, a]))
    expect(byArticle['Article 9'].status).toBe('NON_COMPLIANT')
    expect(byArticle['Article 13'].status).toBe('PARTIAL')
    expect(byArticle['Article 17'].status).toBe('PARTIAL')
  })

  it('MEDIUM risk maps to PARTIAL', async () => {
    installFetch([{
      ok: true,
      body: {
        task_id: 't3',
        plain_english_summary: '',
        generated_at: '',
        eu_ai_act: {
          article_9_risk_management: { risk_assessment: 'MEDIUM' },
        },
      },
    }])
    const { getReport } = await import('../services/api')
    const r = await getReport('t3')
    expect(r.eu_ai_act_compliance[0].status).toBe('PARTIAL')
  })

  it('unknown article keys pass through with key as label', async () => {
    installFetch([{
      ok: true,
      body: {
        task_id: 't4',
        plain_english_summary: '',
        generated_at: '',
        eu_ai_act: { unknown_article: { foo: 'bar' } },
      },
    }])
    const { getReport } = await import('../services/api')
    const r = await getReport('t4')
    expect(r.eu_ai_act_compliance[0].article).toBe('unknown_article')
    expect(r.eu_ai_act_compliance[0].title).toBe('unknown_article')
    expect(r.eu_ai_act_compliance[0].status).toBe('PARTIAL')
    expect(r.eu_ai_act_compliance[0].findings).toContain('foo: bar')
  })

  it('handles completely empty payload', async () => {
    installFetch([{ ok: true, body: {} }])
    const { getReport } = await import('../services/api')
    const r = await getReport('t5')
    expect(r.task_id).toBe('')
    expect(r.plain_english_summary).toBe('')
    expect(r.overall_recommendation).toBe('REVIEW')
    expect(r.confidence_score).toBe(0)
    expect(r.eu_ai_act_compliance).toEqual([])
  })

  it('filters null/undefined/array/object values from findings', async () => {
    installFetch([{
      ok: true,
      body: {
        task_id: 't6',
        plain_english_summary: '',
        generated_at: '',
        eu_ai_act: {
          article_9_risk_management: {
            risk_assessment: 'LOW',
            keep_me: 'yes',
            drop_null: null,
            drop_undef: undefined,
            drop_empty: '',
            drop_array: ['a', 'b'],
            drop_obj: { x: 1 },
          },
        },
      },
    }])
    const { getReport } = await import('../services/api')
    const r = await getReport('t6')
    const findings = r.eu_ai_act_compliance[0].findings
    expect(findings.some(f => f.startsWith('risk assessment:'))).toBe(true)
    expect(findings.some(f => f.startsWith('keep me:'))).toBe(true)
    expect(findings.some(f => f.includes('drop_null'))).toBe(false)
    expect(findings.some(f => f.includes('drop_undef'))).toBe(false)
    expect(findings.some(f => f.includes('drop_empty'))).toBe(false)
    expect(findings.some(f => f.includes('drop_array'))).toBe(false)
    expect(findings.some(f => f.includes('drop_obj'))).toBe(false)
  })

  it('article 9 with missing risk_assessment hits the `?? ""` fallback', async () => {
    installFetch([{
      ok: true,
      body: {
        task_id: 'missing-risk', plain_english_summary: '', generated_at: '',
        eu_ai_act: { article_9_risk_management: {} },
      },
    }])
    const { getReport } = await import('../services/api')
    const r = await getReport('missing-risk')
    // Missing risk_assessment → empty string → neither LOW nor HIGH → PARTIAL
    expect(r.eu_ai_act_compliance[0].status).toBe('PARTIAL')
  })

  it('article 13 reviewer with missing confidence uses the `?? 0` fallback', async () => {
    installFetch([{
      ok: true,
      body: {
        task_id: 'rev-noconf', plain_english_summary: '', generated_at: '',
        eu_ai_act: {
          article_13_transparency: {
            consensus: '1_OF_3_APPROVE',
            reviewers: [{ model: 'gpt-4o', verdict: 'APPROVE' }],  // no confidence
          },
        },
      },
    }])
    const { getReport } = await import('../services/api')
    const r = await getReport('rev-noconf')
    // 0 * 100 = 0 → "0%"
    expect(
      r.eu_ai_act_compliance[0].findings.some(f => f.includes('(0%)')),
    ).toBe(true)
  })

  it('missing overall_recommendation + confidence_score fall back to REVIEW and 0', async () => {
    installFetch([{
      ok: true,
      body: {
        task_id: 'no-rec', plain_english_summary: '', generated_at: '',
        eu_ai_act: {
          // Neither article_9 nor article_13 is present → fallback paths taken
          article_17_quality_management: { all_commitments_verified: true },
        },
      },
    }])
    const { getReport } = await import('../services/api')
    const r = await getReport('no-rec')
    expect(r.overall_recommendation).toBe('REVIEW')
    expect(r.confidence_score).toBe(0)
  })

  it('eu_ai_act entry with null value hits the `val ?? {}` fallback (line 64)', async () => {
    installFetch([{
      ok: true,
      body: {
        task_id: 'null-val', plain_english_summary: '', generated_at: '',
        eu_ai_act: {
          article_9_risk_management: null,  // triggers (val ?? {}) fallback
        },
      },
    }])
    const { getReport } = await import('../services/api')
    const r = await getReport('null-val')
    expect(r.eu_ai_act_compliance).toHaveLength(1)
    expect(r.eu_ai_act_compliance[0].article).toBe('Article 9')
    // With no data fields, no findings extracted
    expect(r.eu_ai_act_compliance[0].findings).toEqual([])
  })
})

describe('api.exportReport + transformExport', () => {
  beforeEach(() => vi.unstubAllGlobals())

  it('maps flat article keys to articles[]', async () => {
    const fetchMock = installFetch([{
      ok: true,
      body: {
        task_id: 'exp1',
        article_9_risk_management:  { risk_assessment: 'LOW', confidence_score: 0.9 },
        article_13_transparency:    { decision_made: 'APPROVE', consensus: '3_OF_3_APPROVE' },
        article_17_quality_management: { all_commitments_verified: true },
      },
    }])
    const { exportReport } = await import('../services/api')
    const r = await exportReport('exp1')
    expect(fetchMock.mock.calls[0][0]).toBe(`${BASE_URL}/api/v1/reports/exp1/export?format=eu_ai_act`)
    expect(r.task_id).toBe('exp1')
    expect(r.export_format).toBe('eu_ai_act')
    expect(r.articles).toHaveLength(3)
    expect(r.articles[0].status).toBe('COMPLIANT')
    expect(r.articles[0].article).toContain('Article 9')
  })

  it('skips articles missing from response', async () => {
    installFetch([{
      ok: true,
      body: {
        task_id: 'exp2',
        article_9_risk_management: { risk_assessment: 'LOW' },
      },
    }])
    const { exportReport } = await import('../services/api')
    const r = await exportReport('exp2')
    expect(r.articles).toHaveLength(1)
    expect(r.articles[0].article).toContain('Article 9')
  })

  it('filters non-scalar values in findings', async () => {
    installFetch([{
      ok: true,
      body: {
        task_id: 'exp3',
        article_9_risk_management: {
          ok_val: 'yes',
          bad_obj: { nested: 1 },
          null_val: null,
        },
      },
    }])
    const { exportReport } = await import('../services/api')
    const r = await exportReport('exp3')
    expect(r.articles[0].findings).toEqual(['ok val: yes'])
  })

  it('empty payload — missing task_id falls through to empty-string default', async () => {
    installFetch([{ ok: true, body: {} }])
    const { exportReport } = await import('../services/api')
    const r = await exportReport('whatever')
    expect(r.task_id).toBe('')
    expect(r.articles).toEqual([])
  })
})
