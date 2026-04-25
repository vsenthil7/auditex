import { useEffect, useState } from 'react'
import * as api from '../../services/api'
import type { HumanOversightPolicy as Policy } from '../../types'

export function OversightConfigPage() {
  const [policies, setPolicies] = useState<Policy[]>([])
  const [originals, setOriginals] = useState<Map<string, Policy>>(new Map())
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState<string | null>(null)
  const [savedAt, setSavedAt] = useState<Map<string, number>>(new Map())
  const [error, setError] = useState<string | null>(null)

  const reload = async () => {
    setLoading(true)
    try {
      const p = (await api.getOversightPolicies()) as Policy[]
      setPolicies(p)
      setOriginals(new Map(p.map((x) => [x.task_type, { ...x }])))
      setError(null)
    } catch (e) { setError((e as Error).message) }
    finally { setLoading(false) }
  }
  useEffect(() => { reload() }, [])

  const isDirty = (p: Policy): boolean => {
    const o = originals.get(p.task_type)
    if (!o) return false
    return o.required !== p.required || o.n_required !== p.n_required || o.m_total !== p.m_total || (o.timeout_minutes ?? null) !== (p.timeout_minutes ?? null) || o.auto_commit_on_timeout !== p.auto_commit_on_timeout
  }

  const updatePolicy = (idx: number, patch: Partial<Policy>) => {
    setPolicies((all) => all.map((it, i) => (i === idx ? { ...it, ...patch } : it)))
  }

  const validate = (p: Policy): string | null => {
    if (p.n_required < 1) return 'N must be >= 1'
    if (p.m_total < p.n_required) return 'M must be >= N'
    if (p.timeout_minutes !== null && p.timeout_minutes < 0) return 'timeout must be >= 0'
    return null
  }

  const save = async (policy: Policy) => {
    const v = validate(policy)
    if (v) { setError(`${policy.task_type}: ${v}`); return }
    setSaving(policy.task_type)
    try {
      await api.updateOversightPolicy(policy.task_type, policy)
      setOriginals((m) => { const next = new Map(m); next.set(policy.task_type, { ...policy }); return next })
      setSavedAt((m) => { const next = new Map(m); next.set(policy.task_type, Date.now()); return next })
      setError(null)
    } catch (e) { setError(`${policy.task_type}: ${(e as Error).message}`) }
    finally { setSaving(null) }
  }

  const reset = (policy: Policy) => {
    const o = originals.get(policy.task_type)
    if (!o) return
    setPolicies((all) => all.map((it) => (it.task_type === policy.task_type ? { ...o } : it)))
  }

  if (loading) return <div className='p-6 text-gray-500'>Loading policies...</div>
  return (
    <div data-testid='oversight-config-page' className='bg-white rounded-lg border border-gray-200 p-6'>
      <div className='flex items-center justify-between mb-4'>
        <div>
          <h2 className='text-lg font-semibold text-gray-800'>Human Oversight Configuration</h2>
          <p className='text-sm text-gray-600 mt-1'>EU AI Act Article 14 - configure required human review per task type. Changes take effect immediately for new tasks.</p>
        </div>
        <button data-testid='reload-policies' onClick={reload} className='px-3 py-1.5 text-sm border border-gray-300 rounded text-gray-700 hover:bg-gray-50'>Reload</button>
      </div>
      {error && <div className='mb-3 p-2 bg-red-50 text-red-700 text-sm rounded border border-red-200' data-testid='config-error'>{error}</div>}
      <div className='overflow-x-auto'>
      <table className='w-full text-sm'>
        <thead className='text-left text-xs uppercase text-gray-500 border-b border-gray-200'>
          <tr>
            <th className='py-2 px-2'>Task type</th>
            <th className='py-2 px-2'>Required</th>
            <th className='py-2 px-2'>N (required)</th>
            <th className='py-2 px-2'>M (total slots)</th>
            <th className='py-2 px-2'>Timeout (min)</th>
            <th className='py-2 px-2'>Auto-commit</th>
            <th className='py-2 px-2' />
          </tr>
        </thead>
        <tbody>
          {policies.map((p, i) => {
            const dirty = isDirty(p)
            const recentlySaved = (savedAt.get(p.task_type) ?? 0) > Date.now() - 3000
            return (
              <tr key={p.task_type} data-testid={`policy-row-${p.task_type}`} className={`border-b border-gray-100 last:border-0 ${dirty ? 'bg-amber-50/40' : ''}`}>
                <td className='py-2 px-2 font-medium text-gray-800'>{p.task_type}</td>
                <td className='py-2 px-2'>
                  <input type='checkbox' data-testid={`required-${p.task_type}`} checked={p.required} onChange={(e) => updatePolicy(i, { required: e.target.checked })} />
                </td>
                <td className='py-2 px-2'>
                  <input type='number' min={1} data-testid={`n-required-${p.task_type}`} className='w-16 border border-gray-300 rounded px-1 py-0.5 text-right' value={p.n_required} onChange={(e) => updatePolicy(i, { n_required: Number(e.target.value) })} />
                </td>
                <td className='py-2 px-2'>
                  <input type='number' min={1} data-testid={`m-total-${p.task_type}`} className='w-16 border border-gray-300 rounded px-1 py-0.5 text-right' value={p.m_total} onChange={(e) => updatePolicy(i, { m_total: Number(e.target.value) })} />
                </td>
                <td className='py-2 px-2'>
                  <input type='number' min={0} placeholder='never' data-testid={`timeout-${p.task_type}`} className='w-24 border border-gray-300 rounded px-1 py-0.5 text-right' value={p.timeout_minutes ?? ''} onChange={(e) => updatePolicy(i, { timeout_minutes: e.target.value === '' ? null : Number(e.target.value) })} />
                </td>
                <td className='py-2 px-2'>
                  <input type='checkbox' data-testid={`auto-commit-${p.task_type}`} checked={p.auto_commit_on_timeout} onChange={(e) => updatePolicy(i, { auto_commit_on_timeout: e.target.checked })} />
                </td>
                <td className='py-2 px-2 text-right space-x-1 whitespace-nowrap'>
                  {dirty && (<button data-testid={`reset-${p.task_type}`} onClick={() => reset(p)} className='px-2 py-0.5 text-xs text-gray-600 hover:text-gray-900 underline'>reset</button>)}
                  <button data-testid={`save-policy-${p.task_type}`} onClick={() => save(p)} disabled={saving === p.task_type || !dirty} className={`px-3 py-1 text-xs rounded text-white ${saving === p.task_type ? 'bg-gray-400' : dirty ? 'bg-blue-600 hover:bg-blue-700' : 'bg-gray-300 cursor-not-allowed'}`}>
                    {saving === p.task_type ? 'Saving...' : dirty ? 'Save' : recentlySaved ? 'Saved' : 'Saved'}
                  </button>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
      </div>
      <p className='text-xs text-gray-500 mt-3'>Tip: leave Timeout empty to wait forever for human decisions. Auto-commit applies only if Timeout is set.</p>
    </div>
  )
}
