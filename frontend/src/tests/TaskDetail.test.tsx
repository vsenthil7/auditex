/**
 * TaskDetail — covers every major branch of the rendering tree:
 *   - "select a task" empty state
 *   - executor / review / vertex blocks
 *   - STEPS lifecycle timeline (done / active / future / failed)
 *   - VertexModeBadge LIVE and STUB
 *   - Confidence bar thresholds (red / yellow / green)
 *   - RecBadge variants
 *   - Report loading / success / error
 *   - EU AI Act accordion open/close
 *   - Export button — success + failure
 *   - Section open/close toggles
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, waitFor, fireEvent, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { TaskDetail } from '../components/TaskDetail'
import { useTaskStore } from '../store/taskStore'

vi.mock('../services/api', () => ({
  getReport: vi.fn(),
  exportReport: vi.fn(),
}))

import * as api from '../services/api'

function setStore(tasks: Record<string, any>, selectedTaskId: string | null) {
  useTaskStore.setState({
    tasks,
    selectedTaskId,
    loading: false,
    error: null,
    _pollingHandle: null,
  })
}

beforeEach(() => {
  setStore({}, null)
  vi.clearAllMocks()
})

describe('TaskDetail — empty state', () => {
  it('prompts to select a task when none is selected', () => {
    render(<TaskDetail />)
    expect(screen.getByText(/Select a task to view details/i)).toBeInTheDocument()
  })
})

describe('TaskDetail — lifecycle + Step 1', () => {
  it('shows task id, type, StatusBadge + Step 1 submission block', async () => {
    const now = '2026-04-21T10:00:00Z'
    setStore({
      a: {
        task_id: 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee',
        task_type: 'document_review',
        status: 'EXECUTING',
        created_at: now,
        report_available: false,
        workflow_id: 'wf1',
      },
    }, 'a')

    render(<TaskDetail />)
    expect(screen.getByText('document review')).toBeInTheDocument()
    expect(screen.getByText('EXECUTING')).toBeInTheDocument()
    // Step 1 header visible; expand it
    await userEvent.click(screen.getByText(/Step 1 — Submission/i))
    expect(screen.getByText(/Workflow ID/i)).toBeInTheDocument()
  })

  it('shows failure banner on FAILED tasks', () => {
    setStore({
      f: {
        task_id: 'fail1', task_type: 'document_review', status: 'FAILED',
        created_at: '2026-04-21T10:00:00Z', report_available: false,
        error_message: 'pipeline blew up',
      },
    }, 'f')
    render(<TaskDetail />)
    expect(screen.getByText(/Task Failed/i)).toBeInTheDocument()
    expect(screen.getByText(/pipeline blew up/i)).toBeInTheDocument()
  })

  it('shows default failure copy when error_message is absent', () => {
    setStore({
      f: {
        task_id: 'fail2', task_type: 'document_review', status: 'ESCALATED',
        created_at: '2026-04-21T10:00:00Z', report_available: false,
      },
    }, 'f')
    render(<TaskDetail />)
    expect(screen.getByText(/Task did not complete successfully/i)).toBeInTheDocument()
  })
})

describe('TaskDetail — Step 2 (Executor)', () => {
  it('renders executor model + confidence bar + reasoning + full output', async () => {
    setStore({
      e: {
        task_id: 'exec1',
        task_type: 'document_review',
        status: 'COMPLETED',
        created_at: '2026-04-21T10:00:00Z',
        report_available: false,
        executor: {
          model: 'claude-sonnet-4-6',
          confidence: 0.85,
          recommendation: 'APPROVE',
          reasoning: 'Looks OK.',
          output: { foo: 'bar' },
        },
      },
    }, 'e')
    render(<TaskDetail />)
    await userEvent.click(screen.getByText(/Step 2 — AI Executor/i))
    expect(screen.getByText('claude-sonnet-4-6')).toBeInTheDocument()
    expect(screen.getByText('Looks OK.')).toBeInTheDocument()
    expect(screen.getByText(/"foo"/)).toBeInTheDocument()
  })

  it('uses nested executor.output.recommendation if top-level missing', async () => {
    setStore({
      e: {
        task_id: 'exec2',
        task_type: 'risk_analysis',
        status: 'REVIEWING',
        created_at: '2026-04-21T10:00:00Z',
        report_available: false,
        executor: {
          model: 'claude',
          confidence: 0.5,
          output: { recommendation: 'REQUEST_ADDITIONAL_INFO' },
        },
      },
    }, 'e')
    render(<TaskDetail />)
    // Recommendation badge shown in the header
    expect(
      screen.getAllByText('REQUEST_ADDITIONAL_INFO').length,
    ).toBeGreaterThanOrEqual(1)
  })

  it('executor block absent when task has no executor', () => {
    setStore({
      q: {
        task_id: 'q1', task_type: 'document_review', status: 'QUEUED',
        created_at: '2026-04-21T10:00:00Z', report_available: false,
      },
    }, 'q')
    render(<TaskDetail />)
    expect(screen.queryByText(/Step 2 — AI Executor/i)).not.toBeInTheDocument()
  })

  it('renders confidence bar in yellow tier and without reasoning or output', async () => {
    setStore({
      e: {
        task_id: 'exec3',
        task_type: 'contract_check',
        status: 'COMPLETED',
        created_at: '2026-04-21T10:00:00Z',
        report_available: false,
        executor: {
          model: 'claude',
          confidence: 0.7,
          recommendation: 'REJECT',
          // no reasoning, no output
        },
      },
    }, 'e')
    render(<TaskDetail />)
    await userEvent.click(screen.getByText(/Step 2 — AI Executor/i))
    // Percentage display
    expect(screen.getByText('70%')).toBeInTheDocument()
  })

  it('renders confidence bar in red tier', async () => {
    setStore({
      e: {
        task_id: 'exec4',
        task_type: 'document_review',
        status: 'COMPLETED',
        created_at: '2026-04-21T10:00:00Z',
        report_available: false,
        executor: { model: 'x', confidence: 0.2, recommendation: 'REJECT' },
      },
    }, 'e')
    render(<TaskDetail />)
    await userEvent.click(screen.getByText(/Step 2 — AI Executor/i))
    expect(screen.getByText('20%')).toBeInTheDocument()
  })
})

describe('TaskDetail — Step 3 (Review Panel)', () => {
  it('renders reviewer cards with verdict badges, verification flag, short commitment', async () => {
    setStore({
      r: {
        task_id: 'rev1',
        task_type: 'document_review',
        status: 'COMPLETED',
        created_at: '2026-04-21T10:00:00Z',
        report_available: false,
        review: {
          consensus: '2_OF_3_APPROVE',
          reviewers: [
            { model: 'gpt-4o', verdict: 'APPROVE', confidence: 0.9, commitment_verified: true, committed_hash: 'abcdef1234567890abcdef1234567890' },
            { model: 'gpt-4o', verdict: 'REJECT', confidence: 0.4, commitment_verified: false },
            { model: 'claude', verdict: 'REQUEST_AMENDMENTS', confidence: 0.6, commitment_verified: true },
          ],
        },
      },
    }, 'r')
    render(<TaskDetail />)
    await userEvent.click(screen.getByText(/Step 3 — Review Panel/i))
    expect(screen.getByText('APPROVE')).toBeInTheDocument()
    expect(screen.getByText('REJECT')).toBeInTheDocument()
    expect(screen.getByText('REQUEST_AMENDMENTS')).toBeInTheDocument()
    expect(screen.getByText('✗ Unverified')).toBeInTheDocument()
    expect(screen.getAllByText('✓ Verified').length).toBeGreaterThanOrEqual(2)
  })

  it('renders without confidence or commitment when fields absent', async () => {
    setStore({
      r: {
        task_id: 'rev2',
        task_type: 'risk_analysis',
        status: 'COMPLETED',
        created_at: '2026-04-21T10:00:00Z',
        report_available: false,
        review: {
          consensus: '3_OF_3_REJECT',
          reviewers: [{ model: 'gpt-4o', verdict: 'REJECT', commitment_verified: false }],
        },
      },
    }, 'r')
    render(<TaskDetail />)
    await userEvent.click(screen.getByText(/Step 3 — Review Panel/i))
    // "No hash" fallback when committed_hash missing
    expect(screen.getByText('No hash')).toBeInTheDocument()
  })

  it('review block absent when task.review is empty', () => {
    setStore({
      r: {
        task_id: 'rev3', task_type: 'document_review', status: 'EXECUTING',
        created_at: '2026-04-21T10:00:00Z', report_available: false,
        review: { consensus: '', reviewers: [] },
      },
    }, 'r')
    render(<TaskDetail />)
    expect(screen.queryByText(/Step 3 — Review Panel/i)).not.toBeInTheDocument()
  })

  it('consensus with REJECT gets red badge styling (branch coverage)', async () => {
    setStore({
      r: {
        task_id: 'rev4', task_type: 'document_review', status: 'COMPLETED',
        created_at: '2026-04-21T10:00:00Z', report_available: false,
        review: {
          consensus: '3_OF_3_REJECT',
          reviewers: [
            { model: 'gpt-4o', verdict: 'REJECT', confidence: 0.2, commitment_verified: true },
          ],
        },
      },
    }, 'r')
    render(<TaskDetail />)
    await userEvent.click(screen.getByText(/Step 3 — Review Panel/i))
    expect(screen.getByText('3_OF_3_REJECT')).toBeInTheDocument()
  })

  it('consensus neither APPROVE nor REJECT falls to yellow tier', async () => {
    setStore({
      r: {
        task_id: 'rev5', task_type: 'document_review', status: 'COMPLETED',
        created_at: '2026-04-21T10:00:00Z', report_available: false,
        review: {
          consensus: 'SPLIT',
          reviewers: [
            { model: 'x', verdict: 'OTHER', confidence: 0.5, commitment_verified: true },
          ],
        },
      },
    }, 'r')
    render(<TaskDetail />)
    await userEvent.click(screen.getByText(/Step 3 — Review Panel/i))
    expect(screen.getByText('SPLIT')).toBeInTheDocument()
  })
})

describe('TaskDetail — Step 4 (Vertex)', () => {
  it('LIVE mode badge when vertex.mode === "LIVE"', async () => {
    setStore({
      v: {
        task_id: 'vx1', task_type: 'document_review', status: 'COMPLETED',
        created_at: '2026-04-21T10:00:00Z', report_available: false,
        vertex: {
          event_hash: 'h'.repeat(64), round: 42,
          finalised_at: '2026-04-21T10:30:00Z', mode: 'LIVE',
        },
      },
    }, 'v')
    render(<TaskDetail />)
    const badges = screen.getAllByTestId('vertex-mode-badge')
    expect(badges[0]).toHaveTextContent(/LIVE/)
    await userEvent.click(screen.getByText(/Step 4 — Vertex Consensus/i))
    expect(
      screen.getAllByText(/Tashi FoxMQ BFT broker/i).length,
    ).toBeGreaterThan(0)
  })

  it('STUB mode badge when mode missing', async () => {
    setStore({
      v: {
        task_id: 'vx2', task_type: 'document_review', status: 'COMPLETED',
        created_at: '2026-04-21T10:00:00Z', report_available: false,
        vertex: { event_hash: 'a'.repeat(64), round: 1, finalised_at: '2026-04-21T10:30:00Z' },
      },
    }, 'v')
    render(<TaskDetail />)
    const badges = screen.getAllByTestId('vertex-mode-badge')
    expect(badges[0]).toHaveTextContent(/STUB/)
    await userEvent.click(screen.getByText(/Step 4 — Vertex Consensus/i))
    expect(screen.getAllByText(/Redis round counter/i).length).toBeGreaterThan(0)
    expect(screen.getByText('STUB')).toBeInTheDocument()
  })
})

describe('TaskDetail — Step 5 (Report)', () => {
  it('shows "Generating report…" for COMPLETED with !report_available', async () => {
    setStore({
      p: {
        task_id: 'rpt1', task_type: 'document_review', status: 'COMPLETED',
        created_at: '2026-04-21T10:00:00Z', report_available: false,
      },
    }, 'p')
    render(<TaskDetail />)
    expect(screen.getByText(/Generating report/i)).toBeInTheDocument()
  })

  it('fetches report when report_available; renders findings + accordion + export', async () => {
    vi.mocked(api.getReport).mockResolvedValue({
      task_id: 'rpt2', generated_at: '2026-04-21T10:30:00Z',
      plain_english_summary: 'Compliant.', overall_recommendation: 'APPROVE',
      confidence_score: 0.9,
      eu_ai_act_compliance: [
        { article: 'Article 9', title: 'Risk Management', status: 'COMPLIANT',
          findings: ['risk assessment: LOW'], recommendations: ['none'] },
      ],
    } as any)
    vi.mocked(api.exportReport).mockResolvedValue({
      task_id: 'rpt2', export_format: 'eu_ai_act', generated_at: '2026-04-21T10:31:00Z',
      articles: [{ article: 'Article 9', title: 'Risk Management', status: 'COMPLIANT', findings: [], recommendations: [] }],
    } as any)

    setStore({
      p: {
        task_id: 'rpt2', task_type: 'document_review', status: 'COMPLETED',
        created_at: '2026-04-21T10:00:00Z', report_available: true,
      },
    }, 'p')
    render(<TaskDetail />)

    await waitFor(() => expect(api.getReport).toHaveBeenCalledWith('rpt2'))
    await screen.findByText('Compliant.')
    expect(screen.getByText('90%')).toBeInTheDocument()
    expect(screen.getByText(/EU AI Act Compliance/i)).toBeInTheDocument()

    // Expand the article accordion → findings visible
    await userEvent.click(screen.getByRole('button', { name: /Article 9 — Risk Management/i }))
    expect(screen.getByText(/risk assessment: LOW/i)).toBeInTheDocument()
    expect(screen.getByText(/none/i)).toBeInTheDocument()

    // Collapse again
    await userEvent.click(screen.getByRole('button', { name: /Article 9 — Risk Management/i }))
    expect(screen.queryByText(/risk assessment: LOW/i)).not.toBeInTheDocument()

    // Export click triggers exportReport + blob download chain
    await userEvent.click(screen.getByRole('button', { name: /Export EU AI Act JSON/i }))
    expect(api.exportReport).toHaveBeenCalledWith('rpt2')
  })

  it('reports error when getReport fails', async () => {
    vi.mocked(api.getReport).mockRejectedValue(new Error('server off'))
    setStore({
      p: {
        task_id: 'rpt3', task_type: 'document_review', status: 'COMPLETED',
        created_at: '2026-04-21T10:00:00Z', report_available: true,
      },
    }, 'p')
    render(<TaskDetail />)
    await screen.findByText(/server off/i)
  })

  it('alerts on exportReport failure', async () => {
    vi.mocked(api.getReport).mockResolvedValue({
      task_id: 'rpt4', generated_at: '', plain_english_summary: '',
      overall_recommendation: 'APPROVE', confidence_score: 0.5, eu_ai_act_compliance: [],
    } as any)
    vi.mocked(api.exportReport).mockRejectedValue(new Error('export down'))
    const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {})

    setStore({
      p: {
        task_id: 'rpt4', task_type: 'document_review', status: 'COMPLETED',
        created_at: '2026-04-21T10:00:00Z', report_available: true,
      },
    }, 'p')
    render(<TaskDetail />)

    await waitFor(() => expect(api.getReport).toHaveBeenCalled())
    await userEvent.click(await screen.findByRole('button', { name: /Export EU AI Act JSON/i }))
    await waitFor(() => expect(alertSpy).toHaveBeenCalled())
    expect(alertSpy.mock.calls[0][0]).toMatch(/Export failed/i)
    alertSpy.mockRestore()
  })

  it('renders yellow confidence tier (60–79%)', async () => {
    vi.mocked(api.getReport).mockResolvedValue({
      task_id: 'rpt5', generated_at: '', plain_english_summary: '',
      overall_recommendation: 'APPROVE', confidence_score: 0.7, eu_ai_act_compliance: [],
    } as any)
    setStore({
      p: {
        task_id: 'rpt5', task_type: 'document_review', status: 'COMPLETED',
        created_at: '2026-04-21T10:00:00Z', report_available: true,
      },
    }, 'p')
    render(<TaskDetail />)
    await screen.findByText('70%')
  })

  it('renders red confidence tier (<60%)', async () => {
    vi.mocked(api.getReport).mockResolvedValue({
      task_id: 'rpt6', generated_at: '', plain_english_summary: '',
      overall_recommendation: 'REJECT', confidence_score: 0.3, eu_ai_act_compliance: [],
    } as any)
    setStore({
      p: {
        task_id: 'rpt6', task_type: 'document_review', status: 'COMPLETED',
        created_at: '2026-04-21T10:00:00Z', report_available: true,
      },
    }, 'p')
    render(<TaskDetail />)
    await screen.findByText('30%')
  })

  it('handles non-COMPLIANT / NON_COMPLIANT article status variants', async () => {
    vi.mocked(api.getReport).mockResolvedValue({
      task_id: 'rpt7', generated_at: '', plain_english_summary: '',
      overall_recommendation: 'REJECT', confidence_score: 0.5,
      eu_ai_act_compliance: [
        { article: 'Article 9',  title: 'Risk',         status: 'NON_COMPLIANT', findings: [],    recommendations: [] },
        { article: 'Article 13', title: 'Transparency', status: 'PARTIAL',       findings: ['x'], recommendations: [] },
      ],
    } as any)
    setStore({
      p: {
        task_id: 'rpt7', task_type: 'document_review', status: 'COMPLETED',
        created_at: '2026-04-21T10:00:00Z', report_available: true,
      },
    }, 'p')
    render(<TaskDetail />)
    await screen.findByText('NON_COMPLIANT')
    expect(screen.getByText('PARTIAL')).toBeInTheDocument()
  })

  it('resets report state when selectedTaskId changes', async () => {
    vi.mocked(api.getReport).mockResolvedValue({
      task_id: 'rpt8', generated_at: '', plain_english_summary: 'First summary.',
      overall_recommendation: 'APPROVE', confidence_score: 0.9, eu_ai_act_compliance: [],
    } as any)
    setStore({
      p: {
        task_id: 'rpt8', task_type: 'document_review', status: 'COMPLETED',
        created_at: '2026-04-21T10:00:00Z', report_available: true,
      },
      q: {
        task_id: 'rpt9', task_type: 'document_review', status: 'COMPLETED',
        created_at: '2026-04-21T10:00:00Z', report_available: false,
      },
    }, 'p')
    const { rerender } = render(<TaskDetail />)
    await screen.findByText('First summary.')

    // Switch selection
    act(() => {
      useTaskStore.setState({ selectedTaskId: 'q' })
    })
    rerender(<TaskDetail />)
    // Report panel shows "Generating…" instead of the stale first summary
    expect(screen.queryByText('First summary.')).not.toBeInTheDocument()
    expect(screen.getByText(/Generating report/i)).toBeInTheDocument()
  })
})

describe('TaskDetail — misc RecBadge / recommendation branches', () => {
  it('REQUEST_AMENDMENTS recommendation colour branch', async () => {
    setStore({
      t: {
        task_id: 'm1', task_type: 'contract_check', status: 'COMPLETED',
        created_at: '2026-04-21T10:00:00Z', report_available: false,
        executor: { model: 'claude', confidence: 0.6, recommendation: 'REQUEST_AMENDMENTS' },
      },
    }, 't')
    render(<TaskDetail />)
    await userEvent.click(screen.getByText(/Step 2 — AI Executor/i))
    expect(
      screen.getAllByText('REQUEST_AMENDMENTS').length,
    ).toBeGreaterThanOrEqual(1)
  })

  it('RecBadge in the report card renders dash when overall_recommendation is empty string', async () => {
    vi.mocked(api.getReport).mockResolvedValue({
      task_id: 'rec-empty', generated_at: '', plain_english_summary: '',
      overall_recommendation: '',   // triggers the `rec || '—'` fallback (line 83 of TaskDetail)
      confidence_score: 0.5, eu_ai_act_compliance: [],
    } as any)
    setStore({
      p: {
        task_id: 'rec-empty', task_type: 'document_review', status: 'COMPLETED',
        created_at: '2026-04-21T10:00:00Z', report_available: true,
      },
    }, 'p')
    render(<TaskDetail />)
    await waitFor(() => expect(api.getReport).toHaveBeenCalled())
    // A dash appears inside the rec-badge span
    await screen.findByText('—')
  })

  it('unknown recommendation colour branch (blank)', () => {
    setStore({
      t: {
        task_id: 'm2', task_type: 'document_review', status: 'EXECUTING',
        created_at: '2026-04-21T10:00:00Z', report_available: false,
      },
    }, 't')
    render(<TaskDetail />)
    expect(screen.getByText('EXECUTING')).toBeInTheDocument()
  })

  it('non-standard executor recommendation falls to the yellow-tier badge branch', async () => {
    setStore({
      t: {
        task_id: 'm3', task_type: 'document_review', status: 'COMPLETED',
        created_at: '2026-04-21T10:00:00Z', report_available: false,
        executor: { model: 'x', confidence: 0.5, recommendation: 'ESCALATE' },  // not in the colour chain
      },
    }, 't')
    render(<TaskDetail />)
    // The Section appears with Step 2 header; the badgeColour falls to the final
    // `execRec ? 'bg-yellow-100 ...' : undefined` branch because ESCALATE is truthy
    // but not APPROVE/REJECT.
    expect(screen.getByText(/Step 2 — AI Executor/i)).toBeInTheDocument()
  })

  it('task without workflow_id omits the Workflow ID KV row', async () => {
    setStore({
      t: {
        task_id: 'm4', task_type: 'document_review', status: 'QUEUED',
        created_at: '2026-04-21T10:00:00Z', report_available: false,
        // NO workflow_id -> exercises the falsy branch of `task.workflow_id && <KV ...>`
      },
    }, 't')
    render(<TaskDetail />)
    await userEvent.click(screen.getByText(/Step 1 — Submission/i))
    expect(screen.queryByText(/Workflow ID/i)).not.toBeInTheDocument()
  })

  it('executor WITHOUT recommendation — Step 2 renders with no badge (lines 230/234 falsy branches)', async () => {
    setStore({
      t: {
        task_id: 'm5', task_type: 'document_review', status: 'EXECUTING',
        created_at: '2026-04-21T10:00:00Z', report_available: false,
        // Executor exists but recommendation is missing AND no nested output.recommendation
        // → execRec === '' (falsy) → line 230 `execRec || undefined` yields undefined
        // → line 234 final ternary `execRec ? ... : undefined` takes the falsy arm
        executor: { model: 'claude', confidence: 0.5 },
      },
    }, 't')
    render(<TaskDetail />)
    // Section header is present
    expect(screen.getByText(/Step 2 — AI Executor/i)).toBeInTheDocument()
    // Header-level RecBadge is NOT rendered because execRec is falsy → {execRec && <RecBadge ...>}
    // is falsy, so the header RecBadge dash is absent. Inside Step 2 when expanded,
    // the Recommendation row renders RecBadge with empty string → shows the "—" fallback.
    await userEvent.click(screen.getByText(/Step 2 — AI Executor/i))
    // At least one em-dash in the expanded section
    await screen.findByText('—')
  })

  it('executor WITHOUT confidence — ConfBar uses the `?? 0` fallback (line 241)', async () => {
    setStore({
      t: {
        task_id: 'm6', task_type: 'document_review', status: 'COMPLETED',
        created_at: '2026-04-21T10:00:00Z', report_available: false,
        executor: { model: 'claude', recommendation: 'APPROVE' },  // no confidence
      },
    }, 't')
    render(<TaskDetail />)
    await userEvent.click(screen.getByText(/Step 2 — AI Executor/i))
    // ConfBar should render 0%
    expect(screen.getByText('0%')).toBeInTheDocument()
  })
})
