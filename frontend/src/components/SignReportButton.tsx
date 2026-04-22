import { useState } from 'react'
import { signReport } from '../services/api'
import type { SignedReportEnvelope } from '../types'

interface Props {
  taskId: string
}

/**
 * Phase 12 (3a) — Sign-report button for completed tasks.
 *
 * Calls POST /api/v1/reports/{taskId}/sign. On success displays the
 * signature_hex, signing_key_id, and algorithm returned by the backend.
 * Provides a "Download signed bundle" link that downloads the full
 * envelope as JSON.
 */
export function SignReportButton({ taskId }: Props) {
  const [signed, setSigned] = useState<SignedReportEnvelope | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSign() {
    setLoading(true)
    setError(null)
    try {
      const envelope = await signReport(taskId)
      setSigned(envelope)
    } catch (e) {
      setError(String(e))
    } finally {
      setLoading(false)
    }
  }

  function handleDownload() {
    const blob = new Blob([JSON.stringify(signed, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `auditex-report-${taskId}-signed.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  if (signed) {
    return (
      <div data-testid="signed-report-details" className="mt-3 rounded-lg border border-green-600 bg-green-50 p-3 text-sm">
        <div className="font-semibold text-green-800 mb-2">Report signed</div>
        <dl className="grid grid-cols-3 gap-x-3 gap-y-1 text-xs">
          <dt className="text-gray-600">Algorithm</dt>
          <dd className="col-span-2 font-mono" data-testid="sig-algorithm">{signed.signature.algorithm}</dd>
          <dt className="text-gray-600">Key ID</dt>
          <dd className="col-span-2 font-mono break-all" data-testid="sig-key-id">{signed.signature.signing_key_id}</dd>
          <dt className="text-gray-600">Signature</dt>
          <dd className="col-span-2 font-mono break-all" data-testid="sig-hex">{signed.signature.signature_hex}</dd>
          <dt className="text-gray-600">Signed at</dt>
          <dd className="col-span-2 font-mono" data-testid="sig-signed-at">{signed.signature.signed_at}</dd>
        </dl>
        <button
          onClick={handleDownload}
          data-testid="download-signed-bundle"
          className="mt-3 w-full rounded-lg border border-green-700 text-green-800 px-4 py-2 text-sm font-semibold hover:bg-green-100 transition-colors"
        >
          ⬇ Download signed bundle
        </button>
      </div>
    )
  }

  return (
    <div className="mt-3">
      <button
        onClick={handleSign}
        disabled={loading}
        data-testid="sign-report-button"
        className="w-full rounded-lg border border-emerald-600 text-emerald-700 px-4 py-2.5 text-sm font-semibold hover:bg-emerald-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {loading ? 'Signing…' : '✒ Sign this report'}
      </button>
      {error && (
        <p data-testid="sign-error" className="mt-2 text-xs text-red-600">{error}</p>
      )}
    </div>
  )
}
