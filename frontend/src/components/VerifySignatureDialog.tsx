import { useState } from 'react'
import { verifyProof } from '../services/api'
import type { VerifyResult } from '../types'

interface Props {
  taskId: string
}

/**
 * Phase 12 (3a) — Verify-signature dialog for completed tasks.
 *
 * Calls GET /api/v1/events/{taskId}/verify and renders each check with a
 * green tick or red cross. Shows expected vs computed hash for diffing.
 * Handles both match (verified=true) and mismatch (verified=false) paths.
 */
export function VerifySignatureDialog({ taskId }: Props) {
  const [result, setResult] = useState<VerifyResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleVerify() {
    setLoading(true)
    setError(null)
    try {
      const r = await verifyProof(taskId)
      setResult(r)
    } catch (e) {
      setError(String(e))
    } finally {
      setLoading(false)
    }
  }

  function handleClose() {
    setResult(null)
    setError(null)
  }

  return (
    <div className="mt-3">
      <button
        onClick={handleVerify}
        disabled={loading}
        data-testid="verify-proof-button"
        className="w-full rounded-lg border border-indigo-600 text-indigo-700 px-4 py-2.5 text-sm font-semibold hover:bg-indigo-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {loading ? 'Verifying…' : '🔍 Verify Vertex proof'}
      </button>
      {error && (
        <p data-testid="verify-error" className="mt-2 text-xs text-red-600">{error}</p>
      )}
      {result && (
        <div
          data-testid="verify-result-panel"
          className={
            'mt-3 rounded-lg border p-3 text-sm ' +
            (result.verified
              ? 'border-green-600 bg-green-50'
              : 'border-amber-600 bg-amber-50')
          }
        >
          <div className="flex items-center justify-between mb-2">
            <span
              className={
                'font-semibold ' +
                (result.verified ? 'text-green-800' : 'text-amber-800')
              }
              data-testid="verify-status"
            >
              {result.verified ? 'Proof verified' : 'Proof NOT verified'}
            </span>
            <button
              onClick={handleClose}
              data-testid="verify-close"
              className="text-xs text-gray-500 hover:text-gray-800"
            >
              ✕ close
            </button>
          </div>

          <ul data-testid="verify-checks" className="space-y-1 mb-3">
            {result.checks.map((c) => (
              <li key={c.name} className="flex items-center gap-2 text-xs">
                <span
                  data-testid={`check-${c.name}`}
                  className={c.ok ? 'text-green-700' : 'text-red-700'}
                >
                  {c.ok ? '✓' : '✗'}
                </span>
                <span className="font-mono">{c.name}</span>
              </li>
            ))}
          </ul>

          <dl className="grid grid-cols-3 gap-x-3 gap-y-1 text-xs">
            <dt className="text-gray-600">Expected</dt>
            <dd className="col-span-2 font-mono break-all" data-testid="verify-expected">
              {result.expected_hash || '(none)'}
            </dd>
            <dt className="text-gray-600">Computed</dt>
            <dd className="col-span-2 font-mono break-all" data-testid="verify-computed">
              {result.computed_hash || '(none)'}
            </dd>
            <dt className="text-gray-600">Events</dt>
            <dd className="col-span-2 font-mono" data-testid="verify-event-count">
              {result.event_count}
            </dd>
            {result.reason && (
              <>
                <dt className="text-gray-600">Reason</dt>
                <dd className="col-span-2" data-testid="verify-reason">
                  {result.reason}
                </dd>
              </>
            )}
          </dl>
        </div>
      )}
    </div>
  )
}
