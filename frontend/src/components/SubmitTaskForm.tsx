import { useState } from 'react'
import { useTaskStore } from '../store/taskStore'
import type { SubmitTaskBody } from '../types'

const TASK_TYPES = ['document_review', 'risk_analysis', 'contract_check'] as const

const CRITERIA = [
  { id: 'completeness',             label: 'Completeness' },
  { id: 'income_verification',      label: 'Income Verification' },
  { id: 'employment_verification',  label: 'Employment Verification' },
  { id: 'risk_assessment',          label: 'Risk Assessment' },
]

export function SubmitTaskForm() {
  const submitTask = useTaskStore((s) => s.submitTask)
  const loading    = useTaskStore((s) => s.loading)

  const [taskType, setTaskType]       = useState<string>(TASK_TYPES[0])
  const [document, setDocument]       = useState('')
  const [criteria, setCriteria]       = useState<string[]>([])
  const [submitError, setSubmitError] = useState<string | null>(null)

  function toggleCriteria(id: string) {
    setCriteria((prev) =>
      prev.includes(id) ? prev.filter((c) => c !== id) : [...prev, id],
    )
  }

  async function handleSubmit() {
    if (!document.trim()) {
      setSubmitError('Document content is required.')
      return
    }
    setSubmitError(null)
    const body: SubmitTaskBody = {
      task_type: taskType,
      document: document.trim(),
      review_criteria: criteria,
    }
    await submitTask(body)
    setDocument('')
    setCriteria([])
  }

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
      <h2 className="text-lg font-semibold text-gray-800 mb-4">Submit New Task</h2>

      <div className="space-y-4">
        {/* Task type */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Task Type</label>
          <select
            value={taskType}
            onChange={(e) => setTaskType(e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {TASK_TYPES.map((t) => (
              <option key={t} value={t}>
                {t.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
              </option>
            ))}
          </select>
        </div>

        {/* Document */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Document <span className="text-red-500">*</span>
          </label>
          <textarea
            rows={5}
            value={document}
            onChange={(e) => setDocument(e.target.value)}
            placeholder="Paste document content here…"
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
          />
        </div>

        {/* Review criteria */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Review Criteria</label>
          <div className="flex flex-wrap gap-3">
            {CRITERIA.map((c) => (
              <label key={c.id} className="flex items-center gap-1.5 text-sm text-gray-700 cursor-pointer">
                <input
                  type="checkbox"
                  checked={criteria.includes(c.id)}
                  onChange={() => toggleCriteria(c.id)}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                {c.label}
              </label>
            ))}
          </div>
        </div>

        {submitError && (
          <p className="text-sm text-red-600">{submitError}</p>
        )}

        <button
          onClick={handleSubmit}
          disabled={loading}
          className="w-full rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white
            hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? 'Submitting…' : 'Submit Task'}
        </button>
      </div>
    </div>
  )
}
