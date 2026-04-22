/**
 * SignReportButton — Phase 12 3a.
 * Covers: initial render, happy-path sign + signed-details render,
 * download triggers createObjectURL, error path, loading state.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { SignReportButton } from '../components/SignReportButton'

vi.mock('../services/api', () => ({
  signReport: vi.fn(),
}))
import { signReport } from '../services/api'

const TASK_ID = 't-1234'

const HAPPY_ENVELOPE = {
  payload: { foo: 'bar' },
  signature: {
    algorithm: 'HMAC-SHA256',
    signing_key_id: 'kid-abc',
    signed_at: '2026-04-22T05:00:00Z',
    signature_hex: 'deadbeef'.repeat(8),
  },
  persisted: true,
}

describe('SignReportButton', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders the initial Sign button', () => {
    render(<SignReportButton taskId={TASK_ID} />)
    expect(screen.getByTestId('sign-report-button')).toBeInTheDocument()
    expect(screen.getByTestId('sign-report-button')).not.toBeDisabled()
  })

  it('signs successfully and renders all signature fields', async () => {
    vi.mocked(signReport).mockResolvedValueOnce(HAPPY_ENVELOPE)
    render(<SignReportButton taskId={TASK_ID} />)

    fireEvent.click(screen.getByTestId('sign-report-button'))

    await waitFor(() => {
      expect(screen.getByTestId('signed-report-details')).toBeInTheDocument()
    })
    expect(signReport).toHaveBeenCalledWith(TASK_ID)
    expect(screen.getByTestId('sig-algorithm')).toHaveTextContent('HMAC-SHA256')
    expect(screen.getByTestId('sig-key-id')).toHaveTextContent('kid-abc')
    expect(screen.getByTestId('sig-hex')).toHaveTextContent('deadbeef')
    expect(screen.getByTestId('sig-signed-at')).toHaveTextContent('2026-04-22T05:00:00Z')
    expect(screen.getByTestId('download-signed-bundle')).toBeInTheDocument()
  })

  it('download button triggers createObjectURL and revokeObjectURL', async () => {
    vi.mocked(signReport).mockResolvedValueOnce(HAPPY_ENVELOPE)
    const createSpy = vi.spyOn(URL, 'createObjectURL')
    const revokeSpy = vi.spyOn(URL, 'revokeObjectURL')

    render(<SignReportButton taskId={TASK_ID} />)
    fireEvent.click(screen.getByTestId('sign-report-button'))
    await waitFor(() => screen.getByTestId('download-signed-bundle'))

    fireEvent.click(screen.getByTestId('download-signed-bundle'))
    expect(createSpy).toHaveBeenCalledTimes(1)
    expect(revokeSpy).toHaveBeenCalledTimes(1)
  })

  it('renders error when signReport throws', async () => {
    vi.mocked(signReport).mockRejectedValueOnce(new Error('API 503: no key'))
    render(<SignReportButton taskId={TASK_ID} />)

    fireEvent.click(screen.getByTestId('sign-report-button'))

    await waitFor(() => {
      expect(screen.getByTestId('sign-error')).toBeInTheDocument()
    })
    expect(screen.getByTestId('sign-error')).toHaveTextContent('API 503: no key')
    // Sign button still visible (not in signed state)
    expect(screen.getByTestId('sign-report-button')).toBeInTheDocument()
  })

  it('shows Signing… while in-flight and disables the button', async () => {
    let resolveIt: (v: typeof HAPPY_ENVELOPE) => void = () => {}
    vi.mocked(signReport).mockReturnValueOnce(
      new Promise((resolve) => { resolveIt = resolve }),
    )
    render(<SignReportButton taskId={TASK_ID} />)

    fireEvent.click(screen.getByTestId('sign-report-button'))

    const btn = screen.getByTestId('sign-report-button')
    expect(btn).toBeDisabled()
    expect(btn).toHaveTextContent(/Signing/)

    resolveIt(HAPPY_ENVELOPE)
    await waitFor(() => screen.getByTestId('signed-report-details'))
  })
})
