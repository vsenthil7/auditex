
import { useEffect, useState } from 'react'
import * as api from '../../services/api'
import type { Task } from '../../types'
import { StatusBadge } from '../StatusBadge'

type Decision = 'APPROVE' | 'REJECT' | 'REQUEST_AMENDMENTS'

interface DecisionState {
  decision: Decision
  reason: string
  reviewed_by: string
}

export function HumanReviewPage() {
  const [queue, setQueue] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedTask, setSelectedTask] = useState<Task | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [feedback, setFeedback] = useState<string | null>(null)
  const [form, setForm] = useState<DecisionState>({ decision: 'APPROVE', reason: '', reviewed_by: '' })

  const load = async () => {
    try {
      const r = await api.listHumanReviewQueue()
      setQueue(r)
      setError(null)
    } catch (e) { setError((e as Error).message) }
    finally { setLoading(false) }
  }

  useEffect(() => {
    load()
    const t = setInterval(load, 5000)
    return () => clearInterval(t)
  }, [])

  const submit = async () => {
    if (!selectedTask) return
    if (!form.reviewed_by.trim() || !form.reason.trim()) {
      setFeedback('reviewer name and reason are both required')
      return
    }
    setSubmitting(true)
    setFeedback(null)
    try {
      await api.submitHumanDecision(selectedTask.task_id, { decision: form.decision, reason: form.reason, reviewed_by: form.reviewed_by })
      setFeedback(`Decision recorded: ${form.decision}`)
      setForm({ decision: 'APPROVE', reason: '', reviewed_by: form.reviewed_by })
      setSelectedTask(null)
      await load()
    } catch (e) { setFeedback(`Failed: ${(e as Error).message}`) }
    finally { setSubmitting(false) }
  }

  if (loading) return <div className='p-6 text-gray-500'>Loading review queue...</div>
  if (error) return <div className='p-6 text-red-700'>Error: {error}</div>

  return (
    <div data-testid='human-review-page' className='grid grid-cols-1 lg:grid-cols-2 gap-4'>
      <div className='bg-white rounded-lg border border-gray-200 p-6'>
        <div className='flex items-center justify-between mb-4'>
          <h2 className='text-lg font-semibold text-gray-800'>Human Review Queue ({queue.length})</h2>
          <button onClick={load} className='text-xs px-2 py-1 border rounded text-gray-600 hover:bg-gray-50'>Refresh</button>
        </div>
        <p className='text-xs text-gray-500 mb-3'>EU AI Act Article 14 - tasks requiring natural-person sign-off before Vertex commitment.</p>
        {queue.length === 0 && <p className='text-sm text-gray-500 py-6 text-center'>No tasks awaiting human review.</p>}
        <ul className='space-y-2'>
          {queue.map((t) => (
            <li key={t.task_id}>
              <button data-testid={`queue-task-${t.task_id.slice(0, 8)}`} onClick={() => { setSelectedTask(t); setFeedback(null) }} className={`w-full text-left border rounded-md p-3 hover:bg-amber-50 transition ${selectedTask?.task_id === t.task_id ? 'border-amber-400 bg-amber-50' : 'border-gray-200'}`}>
                <div className='flex items-center justify-between'>
                  <div>
                    <div className='font-mono text-xs text-gray-500'>{t.task_id.slice(0, 8)}</div>
                    <div className='text-sm font-medium text-gray-800'>{t.task_type}</div>
                  </div>
                  <StatusBadge status={t.status} />
                </div>
              </button>
            </li>
          ))}
        </ul>
      </div>

      <div className='bg-white rounded-lg border border-gray-200 p-6'>
        <h2 className='text-lg font-semibold text-gray-800 mb-4'>Decision Form</h2>
        {feedback && !selectedTask && <p data-testid='decision-feedback' className='mb-3 p-2 bg-green-50 border border-green-200 rounded text-sm text-green-800'>{feedback}</p>}
        {!selectedTask ? (
          <p className='text-sm text-gray-500'>Select a task from the queue to record your decision.</p>
        ) : (
          <div data-testid='decision-form'>
            <div className='mb-3 p-3 bg-gray-50 rounded text-xs space-y-1'>
              <div><span className='text-gray-500'>Task ID:</span> <span className='font-mono'>{selectedTask.task_id}</span></div>
              <div><span className='text-gray-500'>Type:</span> {selectedTask.task_type}</div>
            </div>
            <label className='block text-sm font-medium text-gray-700 mb-1'>Reviewer (your name / id)</label>
            <input data-testid='decision-reviewed-by' type='text' className='w-full border rounded-md px-2 py-1 mb-3 text-sm' value={form.reviewed_by} onChange={e => setForm({ ...form, reviewed_by: e.target.value })} placeholder='jane.smith@bank.example' />
            <label className='block text-sm font-medium text-gray-700 mb-1'>Decision</label>
            <div className='flex gap-2 mb-3'>
              {(['APPROVE', 'REJECT', 'REQUEST_AMENDMENTS'] as Decision[]).map(d => (
                <button key={d} data-testid={`decision-${d}`} onClick={() => setForm({ ...form, decision: d })} className={`flex-1 text-xs px-3 py-2 rounded-md border ${form.decision === d ? (d === 'APPROVE' ? 'bg-green-50 border-green-400 text-green-700' : d === 'REJECT' ? 'bg-red-50 border-red-400 text-red-700' : 'bg-amber-50 border-amber-400 text-amber-700') : 'border-gray-200 text-gray-600 hover:bg-gray-50'}`}>{d}</button>
              ))}
            </div>
            <label className='block text-sm font-medium text-gray-700 mb-1'>Reason / justification</label>
            <textarea data-testid='decision-reason' className='w-full border rounded-md px-2 py-1 mb-3 text-sm h-24' value={form.reason} onChange={e => setForm({ ...form, reason: e.target.value })} placeholder='Why are you approving / rejecting / requesting amendments? This becomes part of the audit chain.' />
            <div className='flex gap-2'>
              <button data-testid='decision-submit' onClick={submit} disabled={submitting} className='flex-1 px-3 py-2 bg-blue-600 text-white text-sm rounded-md disabled:opacity-50'>{submitting ? 'Recording...' : 'Record Decision'}</button>
              <button onClick={() => { setSelectedTask(null); setFeedback(null) }} className='px-3 py-2 border border-gray-200 text-sm rounded-md text-gray-600'>Cancel</button>
            </div>
            {feedback && <p data-testid='decision-feedback' className='mt-3 text-sm text-gray-700'>{feedback}</p>}
          </div>
        )}
      </div>
    </div>
  )
}
