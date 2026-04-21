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

// ── Collapsible Section ──────────────────────────────────────────────────────
function Section({
  title, badge, badgeColour, defaultOpen = false, children,
}: {
  title: string
  badge?: string
  badgeColour?: string
  defaultOpen?: boolean
  children: React.ReactNode
}) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="border border-gray-200 rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-4 py-3 bg-gray-50 hover:bg-gray-100 transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-gray-700 uppercase tracking-wide">{title}</span>
          {badge && (
            <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${badgeColour ?? 'bg-gray-100 text-gray-600'}`}>
              {badge}
            </span>
          )}
        </div>
        <span className="text-gray-400 text-xs">{open ? '▲' : '▼'}</span>
      </button>
      {open && <div className="px-4 py-4 space-y-3 bg-white">{children}</div>}
    </div>
  )
}

// ── KV row ───────────────────────────────────────────────────────────────────
function KV({ k, v, mono = false }: { k: string; v: React.ReactNode; mono?: boolean }) {
  return (
    <div className="flex gap-2 text-sm">
      <span className="text-gray-400 w-36 shrink-0 font-medium">{k}</span>
      <span className={`text-gray-800 break-all flex-1 ${mono ? 'font-mono text-xs' : ''}`}>{v}</span>
    </div>
  )
}

// ── Confidence bar ───────────────────────────────────────────────────────────
function ConfBar({ value }: { value: number }) {
  const pct = Math.round(value * 100)
  const col = pct >= 80 ? 'bg-green-500' : pct >= 60 ? 'bg-yellow-400' : 'bg-red-400'
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 bg-gray-200 rounded-full h-1.5 overflow-hidden">
        <div className={`${col} h-1.5 rounded-full`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-mono text-gray-600 w-9 text-right">{pct}%</span>
    </div>
  )
}

// ── Recommendation badge ──────────────────────────────────────────────────────
function RecBadge({ rec }: { rec: string }) {
  const colour =
    rec === 'APPROVE'                ? 'bg-green-100 text-green-700' :
    rec === 'REJECT'                 ? 'bg-red-100 text-red-700' :
    rec === 'REQUEST_AMENDMENTS'     ? 'bg-orange-100 text-orange-700' :
    rec === 'REQUEST_ADDITIONAL_INFO'? 'bg-yellow-100 text-yellow-700' :
    'bg-gray-100 text-gray-600'
  return <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${colour}`}>{rec || '—'}</span>
}

// ── Vertex mode badge ─────────────────────────────────────────────────────────
function VertexModeBadge({ mode }: { mode?: string }) {
  const isLive = mode === 'LIVE'
  return (
    <span
      data-testid="vertex-mode-badge"
      className={`inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-1 rounded-full border
        ${isLive
          ? 'bg-green-50 text-green-700 border-green-200'
          : 'bg-yellow-50 text-yellow-700 border-yellow-200'
        }`}
    >
      <span className={`w-2 h-2 rounded-full ${isLive ? 'bg-green-500' : 'bg-yellow-400'}`} />
      {isLive ? 'Vertex: LIVE (FoxMQ BFT)' : 'Vertex: STUB (Redis counter)'}
    </span>
  )
}

export function TaskDetail() {
  const tasks          = useTaskStore(s => s.tasks)
  const selectedTaskId = useTaskStore(s => s.selectedTaskId)
  const task           = selectedTaskId ? tasks[selectedTaskId] : null

  const [report, setReport]               = useState<PoCReport | null>(null)
  const [reportLoading, setReportLoading] = useState(false)
  const [reportError, setReportError]     = useState<string | null>(null)
  const [openArticle, setOpenArticle]     = useState<string | null>(null)

  useEffect(() => {
    setReport(null); setReportError(null); setOpenArticle(null)
  }, [selectedTaskId])

  useEffect(() => {
    if (!task || !task.report_available || report) return
    setReportLoading(true)
    getReport(task.task_id)
      .then(r => { setReport(r); setReportLoading(false) })
      .catch(e => { setReportError(String(e)); setReportLoading(false) })
  }, [task?.report_available, task?.task_id])

  async function handleExport() {
    if (!task) return
    try {
      const data = await exportReport(task.task_id)
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const url  = URL.createObjectURL(blob)
      const a    = document.createElement('a')
      a.href = url; a.download = `auditex-report-${task.task_id}.json`; a.click()
      URL.revokeObjectURL(url)
    } catch (e) { alert(`Export failed: ${e}`) }
  }

  if (!task) {
    return (
      <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm flex items-center justify-center min-h-[200px]">
        <p className="text-sm text-gray-400">Select a task to view details.</p>
      </div>
    )
  }

  const isFailed    = task.status === 'FAILED' || task.status === 'ESCALATED'
  const isCompleted = task.status === 'COMPLETED'
  const currentOrder = STATUS_ORDER[task.status]

  const execRec = (task.executor as any)?.recommendation ?? (task.executor as any)?.output?.recommendation ?? ''

  return (
    <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-y-auto" data-testid="task-detail">

      {/* ── Header ─────────────────────────────────────────────────────── */}
      <div className="px-6 py-4 border-b border-gray-100 flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-xs text-gray-400 font-mono truncate">{task.task_id}</p>
          <p className="text-base font-semibold text-gray-800 capitalize mt-0.5">
            {task.task_type.replace(/_/g, ' ')}
          </p>
          {execRec && (
            <div className="mt-1.5"><RecBadge rec={execRec} /></div>
          )}
        </div>
        <div className="flex flex-col items-end gap-1.5">
          <StatusBadge status={task.status} />
          {/* Vertex mode badge — shown as soon as vertex proof exists */}
          {task.vertex && <VertexModeBadge mode={(task.vertex as any).mode} />}
        </div>
      </div>

      <div className="px-4 py-4 space-y-3">

        {/* ── Lifecycle Timeline ─────────────────────────────────────────── */}
        <div className="px-2 py-3">
          <div className="flex items-center gap-0 mt-1">
            {STAGES.map((stage, i) => {
              const done   = isCompleted ? true : currentOrder > STATUS_ORDER[stage.status]
              const active = !isCompleted && task.status === stage.status
              const future = !isCompleted && currentOrder < STATUS_ORDER[stage.status]
              return (
                <div key={stage.status} className="flex items-center flex-1">
                  <div className="flex flex-col items-center flex-1">
                    <div className={`w-3 h-3 rounded-full border-2 transition-all
                      ${isFailed && active  ? 'bg-red-500 border-red-500 ring-2 ring-red-200' : ''}
                      ${done && !isFailed   ? 'bg-green-500 border-green-500' : ''}
                      ${active && !isFailed ? 'bg-blue-500 border-blue-500 ring-2 ring-blue-200' : ''}
                      ${future             ? 'bg-white border-gray-300' : ''}`}
                    />
                    <span className={`text-xs mt-1 ${
                      future ? 'text-gray-300' :
                      isFailed && active ? 'text-red-500' : 'text-gray-600'}`}>
                      {stage.label}
                    </span>
                  </div>
                  {i < STAGES.length - 1 && (
                    <div className={`h-0.5 flex-1 mb-4 ${
                      isFailed ? 'bg-red-200' :
                      done || active ? 'bg-green-300' : 'bg-gray-200'}`}
                    />
                  )}
                </div>
              )
            })}
          </div>

          {isFailed && (
            <div className="mt-3 rounded-lg bg-red-50 border border-red-200 px-4 py-3">
              <p className="text-xs font-semibold text-red-700 mb-1">Task Failed</p>
              <p className="text-xs text-red-600">{task.error_message ?? 'Task did not complete successfully.'}</p>
            </div>
          )}
        </div>

        {/* ── Step 1: Submission Input ────────────────────────────────────── */}
        <Section title="Step 1 — Submission" badge="Input" badgeColour="bg-blue-100 text-blue-700">
          <p className="text-xs text-gray-400 mb-2">What was submitted to the pipeline</p>
          <KV k="Task ID"   v={task.task_id} mono />
          <KV k="Task Type" v={task.task_type} />
          <KV k="Submitted" v={new Date(task.created_at).toLocaleString()} />
          {task.workflow_id && <KV k="Workflow ID" v={task.workflow_id} mono />}
        </Section>

        {/* ── Step 2: Executor Output ─────────────────────────────────────── */}
        {task.executor && (
          <Section
            title="Step 2 — AI Executor"
            badge={execRec || undefined}
            badgeColour={
              execRec === 'APPROVE' ? 'bg-green-100 text-green-700' :
              execRec === 'REJECT'  ? 'bg-red-100 text-red-700' :
              execRec ? 'bg-yellow-100 text-yellow-700' : undefined
            }
          >
            <p className="text-xs text-gray-400 mb-2">Claude Sonnet executed the task and returned a structured verdict</p>
            <KV k="Model" v={task.executor.model} mono />
            <div className="flex gap-2 text-sm">
              <span className="text-gray-400 w-36 shrink-0 font-medium">Confidence</span>
              <div className="flex-1"><ConfBar value={task.executor.confidence ?? 0} /></div>
            </div>
            <div className="flex gap-2 text-sm items-center">
              <span className="text-gray-400 w-36 shrink-0 font-medium">Recommendation</span>
              <RecBadge rec={execRec} />
            </div>
            {task.executor.reasoning && (
              <div>
                <p className="text-xs text-gray-400 mb-1">Reasoning</p>
                <p className="text-sm text-gray-700 bg-gray-50 rounded-lg p-3 leading-relaxed">{task.executor.reasoning}</p>
              </div>
            )}
            {task.executor.output && Object.keys(task.executor.output).length > 0 && (
              <div>
                <p className="text-xs text-gray-400 mb-1">Full Output</p>
                <pre className="text-xs text-gray-700 bg-gray-50 rounded-lg p-3 overflow-x-auto whitespace-pre-wrap">
                  {JSON.stringify(task.executor.output, null, 2)}
                </pre>
              </div>
            )}
          </Section>
        )}

        {/* ── Step 3: Review Panel ────────────────────────────────────────── */}
        {task.review && task.review.reviewers && task.review.reviewers.length > 0 && (
          <Section
            title="Step 3 — Review Panel"
            badge={task.review.consensus}
            badgeColour={
              task.review.consensus?.includes('APPROVE') ? 'bg-green-100 text-green-700' :
              task.review.consensus?.includes('REJECT')  ? 'bg-red-100 text-red-700' :
              'bg-yellow-100 text-yellow-700'
            }
          >
            <p className="text-xs text-gray-400 mb-2">
              3 independent AI reviewers each assessed the executor output and cast a verified vote
            </p>
            <div className="space-y-2">
              {task.review.reviewers.map((r: any, i: number) => (
                <div key={i} className="rounded-lg border border-gray-100 bg-gray-50 p-3 space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold text-gray-700">{r.model}</span>
                      <span className="text-xs text-gray-400">Reviewer {i + 1}</span>
                    </div>
                    <span className={`text-xs font-semibold px-2 py-0.5 rounded-full
                      ${r.verdict === 'APPROVE' ? 'bg-green-100 text-green-700' :
                        r.verdict === 'REJECT'  ? 'bg-red-100 text-red-700' :
                        'bg-yellow-100 text-yellow-700'}`}>
                      {r.verdict}
                    </span>
                  </div>
                  {r.confidence !== undefined && (
                    <div>
                      <p className="text-xs text-gray-400 mb-0.5">Confidence</p>
                      <ConfBar value={r.confidence} />
                    </div>
                  )}
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-gray-400 font-mono truncate max-w-[200px]">
                      {r.committed_hash ? r.committed_hash.slice(0, 24) + '…' : 'No hash'}
                    </span>
                    <span className={`font-medium ${r.commitment_verified ? 'text-green-600' : 'text-red-500'}`}>
                      {r.commitment_verified ? '✓ Verified' : '✗ Unverified'}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </Section>
        )}

        {/* ── Step 4: Vertex Consensus Proof ──────────────────────────────── */}
        {task.vertex && (
          <Section title="Step 4 — Vertex Consensus" badge="Immutable" badgeColour="bg-purple-100 text-purple-700">
            {/* Mode banner — most important thing for judges */}
            <div className="mb-3">
              <VertexModeBadge mode={(task.vertex as any).mode} />
            </div>
            <p className="text-xs text-gray-400 mb-2">
              {(task.vertex as any).mode === 'LIVE'
                ? 'Event published to Tashi FoxMQ BFT broker. Consensus timestamp from hashgraph DAG.'
                : 'Stub mode: real SHA-256 hash + Redis round counter. No distributed consensus.'}
            </p>
            <KV k="Event Hash"   v={(task.vertex as any).event_hash} mono />
            <KV k="Round"        v={String((task.vertex as any).round)} />
            <KV k="Finalised At" v={new Date((task.vertex as any).finalised_at).toLocaleString()} />
            <KV k="Mode"         v={(task.vertex as any).mode ?? 'STUB'} />
          </Section>
        )}

        {/* ── Step 5: Report ──────────────────────────────────────────────── */}
        {isCompleted && (
          <Section
            title="Step 5 — Compliance Report"
            badge={task.report_available ? 'Ready' : 'Generating...'}
            badgeColour={task.report_available ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'}
            defaultOpen={true}
          >
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
                <div className="rounded-lg bg-blue-50 border border-blue-100 p-4" data-testid="plain-english-summary">
                  <p className="text-xs font-semibold text-blue-700 uppercase tracking-wide mb-2">Plain English Summary</p>
                  <pre className="text-sm text-gray-800 whitespace-pre-wrap font-sans leading-relaxed">
                    {report.plain_english_summary}
                  </pre>
                </div>

                <div className="flex gap-3 text-sm">
                  <div className="flex-1 rounded-lg bg-gray-50 border border-gray-100 p-3">
                    <p className="text-xs text-gray-400 mb-1">Recommendation</p>
                    <RecBadge rec={report.overall_recommendation} />
                  </div>
                  <div className="rounded-lg bg-gray-50 border border-gray-100 p-3 text-center min-w-[80px]">
                    <p className="text-xs text-gray-400 mb-1">Confidence</p>
                    <p className={`text-2xl font-bold
                      ${report.confidence_score >= 0.8 ? 'text-green-600' :
                        report.confidence_score >= 0.6 ? 'text-yellow-500' : 'text-red-500'}`}>
                      {(report.confidence_score * 100).toFixed(0)}%
                    </p>
                  </div>
                </div>

                {report.eu_ai_act_compliance?.length > 0 && (
                  <div data-testid="eu-ai-act-compliance">
                    <p className="text-xs font-semibold text-gray-600 uppercase tracking-wide mb-2">EU AI Act Compliance</p>
                    <div className="space-y-2">
                      {report.eu_ai_act_compliance.map((art: any) => (
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
                              {art.findings?.length > 0 && (
                                <div>
                                  <p className="text-xs font-semibold text-gray-400 mb-1">Findings</p>
                                  <ul className="list-disc list-inside space-y-1 text-gray-700">
                                    {art.findings.map((f: string, fi: number) => <li key={fi}>{f}</li>)}
                                  </ul>
                                </div>
                              )}
                              {art.recommendations?.length > 0 && (
                                <div>
                                  <p className="text-xs font-semibold text-gray-400 mb-1">Recommendations</p>
                                  <ul className="list-disc list-inside space-y-1 text-gray-700">
                                    {art.recommendations.map((rec: string, ri: number) => <li key={ri}>{rec}</li>)}
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
          </Section>
        )}

      </div>
    </div>
  )
}
