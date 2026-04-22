import type {
  Task,
  TaskListResponse,
  SubmitTaskBody,
  PoCReport,
  EuAiActExport,
  SignedReportEnvelope,
  VerifyResult,
} from '../types'

const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
const API_KEY  = import.meta.env.VITE_API_KEY  ?? 'auditex-test-key-phase2'

const DEFAULT_AGENT_ID = 'ede4995c-4129-4066-8d96-fa8e246a4a10'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': API_KEY,
      ...(init?.headers ?? {}),
    },
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`API ${res.status}: ${text}`)
  }
  return res.json() as Promise<T>
}

export async function submitTask(body: SubmitTaskBody): Promise<Task> {
  return request<Task>('/api/v1/tasks', {
    method: 'POST',
    body: JSON.stringify({
      task_type: body.task_type,
      payload: {
        document:        body.document,
        review_criteria: body.review_criteria,
        agent_id:        DEFAULT_AGENT_ID,
      },
    }),
  })
}

export async function getTask(id: string): Promise<Task> {
  return request<Task>(`/api/v1/tasks/${id}`)
}

export async function listTasks(page = 1, size = 50): Promise<TaskListResponse> {
  return request<TaskListResponse>(`/api/v1/tasks?page=${page}&page_size=${size}`)
}

// Transform backend eu_ai_act flat dict Ã¢â€ â€™ frontend eu_ai_act_compliance array
function transformReport(raw: Record<string, unknown>): PoCReport {
  const eu = (raw.eu_ai_act ?? {}) as Record<string, Record<string, unknown>>

  const articleMap: Record<string, { label: string; title: string }> = {
    article_9_risk_management:       { label: 'Article 9',  title: 'Risk Management' },
    article_13_transparency:         { label: 'Article 13', title: 'Transparency' },
    article_17_quality_management:   { label: 'Article 17', title: 'Quality Management' },
  }

  const eu_ai_act_compliance = Object.entries(eu).map(([key, val]) => {
    const meta   = articleMap[key] ?? { label: key, title: key }
    const data   = (val ?? {}) as Record<string, unknown>

    // Derive status from available fields
    let status = 'PARTIAL'
    if (key === 'article_9_risk_management') {
      const risk = String(data.risk_assessment ?? '')
      status = risk === 'LOW' ? 'COMPLIANT' : risk === 'HIGH' ? 'NON_COMPLIANT' : 'PARTIAL'
    } else if (key === 'article_13_transparency') {
      status = data.consensus ? 'COMPLIANT' : 'PARTIAL'
    } else if (key === 'article_17_quality_management') {
      status = data.all_commitments_verified ? 'COMPLIANT' : 'PARTIAL'
    }

    // Build findings from the data fields
    const findings: string[] = []
    Object.entries(data).forEach(([k, v]) => {
      if (v !== null && v !== undefined && v !== '' && !Array.isArray(v) && typeof v !== 'object') {
        findings.push(`${k.replace(/_/g, ' ')}: ${v}`)
      }
    })

    // Reviewers as findings for article 13
    if (key === 'article_13_transparency' && Array.isArray(data.reviewers)) {
      ;(data.reviewers as Record<string, unknown>[]).forEach((r) => {
        findings.push(`${r.model}: ${r.verdict} (${((r.confidence as number ?? 0) * 100).toFixed(0)}%)`)
      })
    }

    return {
      article:         meta.label,
      title:           meta.title,
      status,
      findings,
      recommendations: [],
    }
  })

  return {
    task_id:               String(raw.task_id ?? ''),
    generated_at:          String(raw.generated_at ?? ''),
    plain_english_summary: String(raw.plain_english_summary ?? ''),
    overall_recommendation: String(
      (raw.eu_ai_act as Record<string, Record<string, unknown>> | undefined)
        ?.article_13_transparency?.decision_made ?? 'REVIEW'
    ),
    confidence_score: Number(
      (raw.eu_ai_act as Record<string, Record<string, unknown>> | undefined)
        ?.article_9_risk_management?.confidence_score ?? 0
    ),
    eu_ai_act_compliance,
  }
}

export async function getReport(taskId: string): Promise<PoCReport> {
  const raw = await request<Record<string, unknown>>(`/api/v1/reports/${taskId}`)
  return transformReport(raw)
}

// Transform export: backend returns flat article keys at top level
function transformExport(raw: Record<string, unknown>): EuAiActExport {
  const articleMap: Record<string, string> = {
    article_9_risk_management:     'Article 9 Ã¢â‚¬â€ Risk Management',
    article_13_transparency:       'Article 13 Ã¢â‚¬â€ Transparency',
    article_17_quality_management: 'Article 17 Ã¢â‚¬â€ Quality Management',
  }
  const articles = Object.entries(articleMap)
    .filter(([key]) => raw[key])
    .map(([key, label]) => ({
      article: label,
      title:   label,
      status:  'COMPLIANT',
      findings: Object.entries(raw[key] as Record<string, unknown>)
        .filter(([, v]) => v !== null && v !== undefined && typeof v !== 'object')
        .map(([k, v]) => `${k.replace(/_/g, ' ')}: ${v}`),
      recommendations: [],
    }))
  return {
    task_id:       String(raw.task_id ?? ''),
    export_format: 'eu_ai_act',
    generated_at:  new Date().toISOString(),
    articles,
  }
}

export async function exportReport(taskId: string): Promise<EuAiActExport> {
  const raw = await request<Record<string, unknown>>(
    `/api/v1/reports/${taskId}/export?format=eu_ai_act`,
  )
  return transformExport(raw)
}


export async function signReport(taskId: string): Promise<SignedReportEnvelope> {
  return request<SignedReportEnvelope>(`/api/v1/reports/${taskId}/sign`, {
    method: 'POST',
  })
}


export async function verifyProof(taskId: string): Promise<VerifyResult> {
  return request<VerifyResult>(`/api/v1/events/${taskId}/verify`)
}
