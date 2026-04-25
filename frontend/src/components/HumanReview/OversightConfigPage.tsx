import { useEffect, useState } from 'react'
import * as api from '../../services/api'
import type { HumanOversightPolicy as Policy } from '../../types'

export function OversightConfigPage() {
  const [policies, setPolicies] = useState<Policy[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const load = async () => {
      try { setPolicies(await api.getOversightPolicies()); setError(null) }
      catch (e) { setError((e as Error).message) }
      finally { setLoading(false) }
    }
    load()
  }, [])

  const updatePolicy = (idx: number, patch: Partial<Policy>) => {
    setPolicies(p => p.map((it, i) => i === idx ? { ...it, ...patch } : it))
  }

  const save = async (p: Policy) => {
    setSaving(p.task_type)
    try { await api.updateOversightPolicy(p.task_type, p); setError(null) }
    catch (e) { setError((e as Error).message) }
    finally { setSaving(null) }
  }

  if (loading) return <div className='p-6 text-gray-500'>Loading policies...</div>
  return (
    <div data-testid='oversight-config-page' className='bg-white rounded-lg border border-gray-200 p-6'>
      <h2 className='text-lg font-semibold text-gray-800 mb-4'>Human Oversight Configuration</h2>
      <p className='text-sm text-gray-600 mb-4'>EU AI Act Article 14 - configure required human review per task type.</p>
      {error && <div className='mb-3 text-sm text-red-700'>Error: {error}</div>}
      <table className='w-full text-sm'>
        <thead className='text-left text-gray-600 border-b'>
          <tr><th className='py-2'>Task type</th><th>Required</th><th>N of M</th><th>Timeout (min)</th><th>Auto-commit</th><th></th></tr>
        </thead>
        <tbody>
          {policies.map((p, i) => (
            <tr key={p.task_type} className='border-b last:border-0'>
              <td className='py-2 font-medium'>{p.task_type}</td>
              <td><input type='checkbox' checked={p.required} onChange={e => updatePolicy(i, { required: e.target.checked })} /></td>
              <td className='space-x-1'>
                <input type='number' min={1} className='w-12 border rounded px-1' value={p.n_required} onChange={e => updatePolicy(i, { n_required: Number(e.target.value) })} />
                <span>/</span>
                <input type='number' min={1} className='w-12 border rounded px-1' value={p.m_total} onChange={e => updatePolicy(i, { m_total: Number(e.target.value) })} />
              </td>
              <td><input type='number' min={0} className='w-20 border rounded px-1' value={p.timeout_minutes ?? ''} onChange={e => updatePolicy(i, { timeout_minutes: e.target.value === '' ? null : Number(e.target.value) })} /></td>
              <td><input type='checkbox' checked={p.auto_commit_on_timeout} onChange={e => updatePolicy(i, { auto_commit_on_timeout: e.target.checked })} /></td>
              <td><button data-testid={'save-policy-' + p.task_type} onClick={() => save(p)} disabled={saving === p.task_type} className='px-2 py-1 text-xs bg-blue-600 text-white rounded disabled:opacity-50'>{saving === p.task_type ? 'Saving...' : 'Save'}</button></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
