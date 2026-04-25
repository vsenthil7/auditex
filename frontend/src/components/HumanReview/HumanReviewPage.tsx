import { useEffect, useState } from 'react'
import * as api from '../../services/api'
import type { Task } from '../../types'
import { StatusBadge } from '../StatusBadge'

export function HumanReviewPage() {
  const [queue, setQueue] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const load = async () => {
      try {
        const r = await api.listHumanReviewQueue()
        setQueue(r)
        setError(null)
      } catch (e) { setError((e as Error).message) }
      finally { setLoading(false) }
    }
    load()
    const t = setInterval(load, 5000)
    return () => clearInterval(t)
  }, [])

  if (loading) return <div className='p-6 text-gray-500'>Loading review queue...</div>
  if (error) return <div className='p-6 text-red-700'>Error: {error}</div>
  return (
    <div data-testid='human-review-page' className='bg-white rounded-lg border border-gray-200 p-6'>
      <h2 className='text-lg font-semibold text-gray-800 mb-4'>Human Review Queue ({queue.length})</h2>
      {queue.length === 0 && <p className='text-sm text-gray-500'>No tasks awaiting human review.</p>}
      <ul className='space-y-2'>
        {queue.map((t) => (
          <li key={t.task_id} className='border border-gray-200 rounded-md p-3 flex items-center justify-between'>
            <div>
              <div className='font-mono text-xs text-gray-500'>{t.task_id.slice(0, 8)}</div>
              <div className='text-sm font-medium text-gray-800'>{t.task_type}</div>
            </div>
            <StatusBadge status={t.status} />
          </li>
        ))}
      </ul>
    </div>
  )
}
