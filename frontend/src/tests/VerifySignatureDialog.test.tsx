/**
 * VerifySignatureDialog — Phase 12 3a.
 * Covers: initial render, verified=true happy path, verified=false mismatch
 * with reason, fetch error, close button resets state, all-green check marks.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { VerifySignatureDialog } from '../components/VerifySignatureDialog'

vi.mock('../services/api', () => ({
  verifyProof: vi.fn(),
}))
import { verifyProof } from '../services/api'

const TASK_ID = 't-verify-1'

const VERIFIED_OK = {
  task_id: TASK_ID,
  verified: true,
  expected_hash: 'abc123',
  computed_hash: 'abc123',
  event_count: 5,
  reason: null,
  checks: [
    { name: 'has_expected_hash', ok: true },
    { name: 'has_events', ok: true },
    { name: 'chain_hash_matches', ok: true },
  ],
}

const VERIFIED_MISMATCH = {
  task_id: TASK_ID,
  verified: false,
  expected_hash: 'aaa',
  computed_hash: 'bbb',
  event_count: 4,
  reason: 'chain hash does not match expected hash (tampered or wrong events)',
  checks: [
    { name: 'has_expected_hash', ok: true },
    { name: 'has_events', ok: true },
    { name: 'chain_hash_matches', ok: false },
  ],
}

describe('VerifySignatureDialog', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders initial Verify button, no panel yet', () => {
    render(<VerifySignatureDialog taskId={TASK_ID} />)
    expect(screen.getByTestId('verify-proof-button')).toBeInTheDocument()
    expect(screen.queryByTestId('verify-result-panel')).toBeNull()
  })

  it('renders verified=true panel with all green checks and no reason row', async () => {
    vi.mocked(verifyProof).mockResolvedValueOnce(VERIFIED_OK)
    render(<VerifySignatureDialog taskId={TASK_ID} />)

    fireEvent.click(screen.getByTestId('verify-proof-button'))

    await waitFor(() => {
      expect(screen.getByTestId('verify-result-panel')).toBeInTheDocument()
    })
    expect(verifyProof).toHaveBeenCalledWith(TASK_ID)
    expect(screen.getByTestId('verify-status')).toHaveTextContent('Proof verified')
    expect(screen.getByTestId('check-has_expected_hash')).toHaveTextContent('✓')
    expect(screen.getByTestId('check-has_events')).toHaveTextContent('✓')
    expect(screen.getByTestId('check-chain_hash_matches')).toHaveTextContent('✓')
    expect(screen.getByTestId('verify-expected')).toHaveTextContent('abc123')
    expect(screen.getByTestId('verify-computed')).toHaveTextContent('abc123')
    expect(screen.getByTestId('verify-event-count')).toHaveTextContent('5')
    expect(screen.queryByTestId('verify-reason')).toBeNull()
  })

  it('renders verified=false panel with red check and reason row', async () => {
    vi.mocked(verifyProof).mockResolvedValueOnce(VERIFIED_MISMATCH)
    render(<VerifySignatureDialog taskId={TASK_ID} />)

    fireEvent.click(screen.getByTestId('verify-proof-button'))

    await waitFor(() => {
      expect(screen.getByTestId('verify-result-panel')).toBeInTheDocument()
    })
    expect(screen.getByTestId('verify-status')).toHaveTextContent('Proof NOT verified')
    expect(screen.getByTestId('check-chain_hash_matches')).toHaveTextContent('✗')
    expect(screen.getByTestId('verify-reason')).toHaveTextContent('tampered')
  })

  it('close button clears the result panel', async () => {
    vi.mocked(verifyProof).mockResolvedValueOnce(VERIFIED_OK)
    render(<VerifySignatureDialog taskId={TASK_ID} />)

    fireEvent.click(screen.getByTestId('verify-proof-button'))
    await waitFor(() => screen.getByTestId('verify-result-panel'))

    fireEvent.click(screen.getByTestId('verify-close'))
    expect(screen.queryByTestId('verify-result-panel')).toBeNull()
  })

  it('renders error when verifyProof throws', async () => {
    vi.mocked(verifyProof).mockRejectedValueOnce(new Error('API 404: no hash'))
    render(<VerifySignatureDialog taskId={TASK_ID} />)

    fireEvent.click(screen.getByTestId('verify-proof-button'))

    await waitFor(() => {
      expect(screen.getByTestId('verify-error')).toBeInTheDocument()
    })
    expect(screen.getByTestId('verify-error')).toHaveTextContent('API 404: no hash')
    expect(screen.queryByTestId('verify-result-panel')).toBeNull()
  })

  it('shows (none) placeholders when hashes are empty strings', async () => {
    vi.mocked(verifyProof).mockResolvedValueOnce({
      task_id: TASK_ID,
      verified: false,
      expected_hash: '',
      computed_hash: '',
      event_count: 0,
      reason: 'no events',
      checks: [
        { name: 'has_expected_hash', ok: false },
        { name: 'has_events', ok: false },
        { name: 'chain_hash_matches', ok: false },
      ],
    })
    render(<VerifySignatureDialog taskId={TASK_ID} />)
    fireEvent.click(screen.getByTestId('verify-proof-button'))
    await waitFor(() => screen.getByTestId('verify-result-panel'))
    expect(screen.getByTestId('verify-expected')).toHaveTextContent('(none)')
    expect(screen.getByTestId('verify-computed')).toHaveTextContent('(none)')
  })

  it('shows Verifying… and disables button while in-flight', async () => {
    let resolveIt: (v: typeof VERIFIED_OK) => void = () => {}
    vi.mocked(verifyProof).mockReturnValueOnce(
      new Promise((r) => { resolveIt = r }),
    )
    render(<VerifySignatureDialog taskId={TASK_ID} />)

    fireEvent.click(screen.getByTestId('verify-proof-button'))
    const btn = screen.getByTestId('verify-proof-button')
    expect(btn).toBeDisabled()
    expect(btn).toHaveTextContent(/Verifying/)

    resolveIt(VERIFIED_OK)
    await waitFor(() => screen.getByTestId('verify-result-panel'))
  })
})
