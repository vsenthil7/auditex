import type {
  Task,
  TaskListResponse,
  SubmitTaskBody,
  PoCReport,
  EuAiActExport,
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
  // API expects: { task_type, payload: { document, review_criteria, agent_id } }
  return request<Task>('/api/v1/tasks', {
    method: 'POST',
    body: JSON.stringify({
      task_type: body.task_type,
      payload: {
        document:         body.document,
        review_criteria:  body.review_criteria,
        agent_id:         DEFAULT_AGENT_ID,
      },
    }),
  })
}

export async function getTask(id: string): Promise<Task> {
  return request<Task>(`/api/v1/tasks/${id}`)
}

export async function listTasks(page = 1, size = 50): Promise<TaskListResponse> {
  // API param is page_size, not size
  return request<TaskListResponse>(`/api/v1/tasks?page=${page}&page_size=${size}`)
}

export async function getReport(taskId: string): Promise<PoCReport> {
  return request<PoCReport>(`/api/v1/reports/${taskId}`)
}

export async function exportReport(taskId: string): Promise<EuAiActExport> {
  return request<EuAiActExport>(
    `/api/v1/reports/${taskId}/export?format=eu_ai_act`,
  )
}
