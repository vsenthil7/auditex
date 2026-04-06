import { useEffect, useState } from 'react'
import { useTaskStore } from '../store/taskStore'
import { StatusBadge } from './StatusBadge'
import { getReport, exportReport } from '../services/api'
import type { PoCReport, TaskStatus } from '../types'

const STAGES: { status: TaskStatus; label: string }[] = [
  { status: 'QUEUED',     label: 'Queued' },
  { status: 'EXECUTING',  label: 'Executing' },
  { status: 'REVIEWING',  label: 'Reviewing' },
  { status: 'FINALISING', label: 'Finalising' },
  { status: 'COMPLETED',  label: 'Completed' },
]

const STATUS_ORDER: Record<string, number> = {
  QUEUED: 0, EXECUTING: 1, REVIEWING: 2, FINALISING: 3, COMPLETED: 4,
  FAILED: 5, ESCALATED: 5,
}

function SectionHeader({ title }: { title: string }) {
  return (
    <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-2 border-b border-gray-100 pb-1">
      {title}
    </h3>
  )
}

function KV({ k, v }: { k: string; v: React.ReactNode }) {
  return (
    <div className="flex gap-2 text-sm">
      <span className="text-gray-500 w-40 shrink-0">{k}</span>
      <span className="text-gray-800 font-mono break-all">{v}</span>
    </div>
  )
}

export function TaskDetail() {
  const tasks          = useTaskStore((s) => s.tasks)
  const selectedTaskId = useTaskStore((s) => s.selectedTaskId)
  const task           = selectedTaskId ? tasks[selectedTaskId] : null

  const [report, setReport]               = useState<PoCReport | null>(null)
  const [reportLoading, setReportLoading] = useState(false)
  const [reportError, setReportError]     = useState<string | null>(null)
  const [openArticle, setOpenArticle]     = useState<string | null>(null)

  useEffect(() => {
    setReport(null)
    setReportError(null)
    setOpenArticle(null)
  }, [selectedTaskId])

  useEffect(() => {
    if (!task || !task.report_available || report) return
    setReportLoading(true)
    getReport(task.task_id)
      .then((r) => { setReport(r); setReportLoading(false) })
      .catch((e) => { setReportError(String(e)); setReportLoading(false) })
  }, [task?.report_available, task?.task_id])

  async function handleExport() {
    if (!task) return
    try {
      const data = await exportReport(task.task_id)
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const url  = URL.createObjectURL(blob)
      const a    = document.createElement('a')
      a.href     = url
      a.download = `auditex-report-${task.task_id}.json`
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      alert(`Export failed: ${e}`)
    }
  }

  if (!task) {
    return (
      <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm flex items-center justify-center min-h-[200px]">
        <p className="text-sm text-gray-400">Select a task to view details.</p>
      </div>
    )
  }

  return (
    <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-y-auto">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between gap-4">
        <div>
          <p className="text-xs text-gray-400 font-mono">{task.task_id}</p>
          <p className="text-base font-semibold text-gray-800 capitalize mt-0.5">
            {task.task_type.replace(/_/g, ' ')}
          </p>
        </div>
        <StatusBadge status={task.status} />
      </div>

      <div className="px-6 py-4 space-y-6">

        {/* Lifecycle Timeline */}
        <div>
          <SectionHeader title="Lifecycle" />
          <div className="flex items-center gap-1 mt-2">
            {STAGES.map((stage, i) => {
              const done   = STATUS_ORDER[task.status] > STATUS_ORDER[stage.status]
              const active = task.status === stage.status
              const future = STATUS_ORDER[task.status] < STATUS_ORDER[stage.status]
              return (
                <div key={stage.status} className="flex items-center flex-1">
                  <div className="flex flex-col items-center flex-1">
                    <div className={`w-3 h-3 rounded-full border-2 transition-all
                      ${done   ? 'bg-green-500 border-green-500' : ''}
                      ${active ? 'bg-blue-500 border-blue-500 ring-2 ring-blue-200' : ''}
                      ${future ? 'bg-white border-gray-300' : ''}`}
                    />
                    <span className={`text-xs mt-1 ${future ? 'text-gray-300' : 'text-gray-600'}`}>
                      {stage.label}
                    </span>
                  </div>
                  {i < STAGES.length - 1 && (
                    <div className={`h-0.5 flex-1 mb-4 ${done || active ? 'bg-blue-300' : 'bg-gray-200'}`} />
                  )}
                </div>
              )
            })}
          </div>
          {(task.status === 'FAILED' || task.status === 'ESCALATED') && (
            <p className="mt-2 text-xs text-red-600">{task.error_message ?? 'Task did not complete.'}</p>
          )}
        </div>

        {/* Executor Output — API field: task.executor */}
        {task.executor && (
          <div>
            <SectionHeader title="Executor Output" />
            <div className="space-y-1">
              <KV k="Model"          v={task.executor.model} />
              <KV k="Confidence"     v={`${((task.executor.confidence ?? 0) * 100).toFixed(1)}%`} />
              <KV k="Recommendation" v={task.executor.recommendation ?? '—'} />
              {task.executor.reasoning && <KV k="Reasoning" v={task.executor.reasoning} />}
              {task.executor.flags && task.executor.flags.length > 0 && (
                <KV k="Flags" v={task.executor.flags.join(', ')} />
              )}
            </div>
          </div>
        )}

        {/* Review Panel — API field: task.review.reviewers[] */}
        {task.review && task.review.reviewers && task.review.reviewers.length > 0 && (
          <div>
            <SectionHeader title="Review Panel" />
            {task.review.consensus && (
              <p className="text-xs text-gray-500 mb-2">Consensus: <span className="font-medium text-gray-700">{task.review.consensus}</span></p>
            )}
            <div className="grid grid-cols-1 gap-3">
              {task.review.reviewers.map((r, i) => (
                <div key={i} className="rounded-lg border border-gray-100 bg-gray-50 p-3 space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-gray-700">{r.model}</span>
                    <span className={`text-xs font-medium px-2 py-0.5 rounded-full
                      ${r.verdict === 'APPROVED' ? 'bg-green-100 text-green-700' :
                        r.verdict === 'REJECTED'  ? 'bg-red-100 text-red-700' :
                        'bg-yellow-100 text-yellow-700'}`}>
                      {r.verdict}
                    </span>
                  </div>
                  <div className="text-xs text-gray-500 font-mono break-all">
                    {r.commitment_hash ? r.commitment_hash.slice(0, 24) + '…' : 'No hash'}
                  </div>
                  <div className="text-xs">
                    <span className={r.commitment_verified ? 'text-green-600' : 'text-red-500'}>
                      {r.commitment_verified ? '✓ Commitment verified' : '✗ Not verified'}
                    </span>
                  </div>
                  {r.notes && <p className="text-xs text-gray-500 italic">{r.notes}</p>}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Vertex Proof — API field: task.vertex */}
        {task.vertex && (
          <div>
            <SectionHeader title="Vertex Proof" />
            <div className="space-y-1">
              <KV k="Event Hash"   v={task.vertex.event_hash} />
              <KV k="Round"        v={String(task.vertex.round)} />
              <KV k="Finalised At" v={new Date(task.vertex.finalised_at).toLocaleString()} />
            </div>
          </div>
        )}

        {/* Report Section */}
        {task.status === 'COMPLETED' && (
          <div>
            <SectionHeader title="Report" />

            {!task.report_available && (
              <p className="text-sm text-gray-400 animate-pulse">Generating report…</p>
            )}
            {task.report_available && reportLoading && (
              <p className="text-sm text-gray-400 animate-pulse">Loading report…</p>
            )}
            {reportError && (
              <p className="text-sm text-red-500">{reportError}</p>
            )}

            {report && (
              <div className="space-y-4">
                <div className="rounded-lg bg-blue-50 border border-blue-100 p-4">
                  <p className="text-xs font-semibold text-blue-700 uppercase tracking-wide mb-2">Plain English Summary</p>
                  <pre className="text-sm text-gray-800 whitespace-pre-wrap font-sans leading-relaxed">
                    {report.plain_english_summary}
                  </pre>
                </div>

                <div className="flex gap-4 text-sm">
                  <div className="flex-1 rounded-lg bg-gray-50 border border-gray-100 p-3">
                    <p className="text-xs text-gray-500 mb-1">Recommendation</p>
                    <p className="font-medium text-gray-800">{report.overall_recommendation}</p>
                  </div>
                  <div className="rounded-lg bg-gray-50 border border-gray-100 p-3 text-center">
                    <p className="text-xs text-gray-500 mb-1">Confidence</p>
                    <p className="text-2xl font-bold text-blue-600">
                      {(report.confidence_score * 100).toFixed(0)}%
                    </p>
                  </div>
                </div>

                {report.eu_ai_act_compliance && report.eu_ai_act_compliance.length > 0 && (
                  <div>
                    <p className="text-xs font-semibold text-gray-700 uppercase tracking-wide mb-2">EU AI Act Compliance</p>
                    <div className="space-y-2">
                      {report.eu_ai_act_compliance.map((art) => (
                        <div key={art.article} className="rounded-lg border border-gray-200 overflow-hidden">
                          <button
                            onClick={() => setOpenArticle(openArticle === art.article ? null : art.article)}
                            className="w-full flex items-center justify-between px-4 py-3 bg-gray-50 hover:bg-gray-100 text-sm font-medium text-gray-800 transition-colors"
                          >
                            <span>{art.article} — {art.title}</span>
                            <div className="flex items-center gap-2">
                              <span className={`text-xs px-2 py-0.5 rounded-full font-semibold
                                ${art.status === 'COMPLIANT'     ? 'bg-green-100 text-green-700' :
                                  art.status === 'NON_COMPLIANT' ? 'bg-red-100 text-red-700' :
                                  'bg-yellow-100 text-yellow-700'}`}>
                                {art.status}
                              </span>
                              <span className="text-gray-400">{openArticle === art.article ? '▲' : '▼'}</span>
                            </div>
                          </button>
                          {openArticle === art.article && (
                            <div className="px-4 py-3 space-y-3 text-sm">
                              {art.findings.length > 0 && (
                                <div>
                                  <p className="text-xs font-semibold text-gray-500 mb-1">Findings</p>
                                  <ul className="list-disc list-inside space-y-1 text-gray-700">
                                    {art.findings.map((f, fi) => <li key={fi}>{f}</li>)}
                                  </ul>
                                </div>
                              )}
                              {art.recommendations.length > 0 && (
                                <div>
                                  <p className="text-xs font-semibold text-gray-500 mb-1">Recommendations</p>
                                  <ul className="list-disc list-inside space-y-1 text-gray-700">
                                    {art.recommendations.map((rec, ri) => <li key={ri}>{rec}</li>)}
                                  </ul>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <button
                  onClick={handleExport}
                  className="w-full rounded-lg border border-blue-600 text-blue-600 px-4 py-2.5 text-sm font-semibold hover:bg-blue-50 transition-colors"
                >
                  ⬇ Export EU AI Act JSON
                </button>
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  )
}
