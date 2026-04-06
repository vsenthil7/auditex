import { create } from 'zustand'
import type { Task, SubmitTaskBody } from '../types'
import * as api from '../services/api'

const POLL_INTERVAL_MS = 3000

function normalise(raw: Partial<Task> & { task_id: string }): Task {
  return {
    task_id:          raw.task_id,
    task_type:        raw.task_type        ?? 'unknown',
    status:           raw.status           ?? 'QUEUED',
    created_at:       raw.created_at       ?? new Date().toISOString(),
    report_available: raw.report_available ?? false,
    workflow_id:      raw.workflow_id,
    executor:         raw.executor         ?? null,
    review:           raw.review           ?? null,
    vertex:           raw.vertex           ?? null,
    error_message:    raw.error_message,
  }
}

interface TaskState {
  tasks: Record<string, Task>
  selectedTaskId: string | null
  loading: boolean
  error: string | null
  _pollingHandle: ReturnType<typeof setInterval> | null
}

interface TaskActions {
  submitTask: (body: SubmitTaskBody) => Promise<void>
  refreshTasks: () => Promise<void>
  selectTask: (id: string) => void
  startPolling: () => void
  stopPolling: () => void
}

type TaskStore = TaskState & TaskActions

export const useTaskStore = create<TaskStore>((set, get) => ({
  tasks: {},
  selectedTaskId: null,
  loading: false,
  error: null,
  _pollingHandle: null,

  submitTask: async (body) => {
    set({ loading: true, error: null })
    try {
      const raw = await api.submitTask(body)
      const task = normalise(raw)
      set((s) => ({
        tasks: { ...s.tasks, [task.task_id]: task },
        selectedTaskId: task.task_id,
        loading: false,
      }))
      get().refreshTasks()
    } catch (err) {
      set({ loading: false, error: String(err) })
    }
  },

  refreshTasks: async () => {
    try {
      const res = await api.listTasks(1, 100)
      const incoming = res.tasks ?? []
      const selectedId = get().selectedTaskId

      // Always fetch full detail for the selected task so Steps 2/3/4 are populated.
      // Also fetch full detail for any active task (so executor/review populate as they complete).
      const enriched = await Promise.all(
        incoming.map(async (t) => {
          const needsFull =
            t.task_id === selectedId ||                           // currently viewed
            ['EXECUTING','REVIEWING','FINALISING'].includes(t.status) || // active — fields change
            (t.status === 'COMPLETED' && !t.report_available)    // waiting for report

          if (needsFull) {
            try {
              return normalise(await api.getTask(t.task_id))
            } catch {
              return normalise(t)
            }
          }

          // For COMPLETED tasks not selected, keep existing enriched data if we have it,
          // otherwise merge list data preserving any existing executor/review/vertex.
          const existing = get().tasks[t.task_id]
          if (existing && (existing.executor || existing.review || existing.vertex)) {
            return normalise({ ...existing, ...t })
          }

          return normalise(t)
        }),
      )

      set((s) => {
        const updated: Record<string, Task> = { ...s.tasks }
        for (const t of enriched) {
          updated[t.task_id] = t
        }
        return { tasks: updated }
      })
    } catch (err) {
      set({ error: String(err) })
    }
  },

  selectTask: async (id) => {
    set({ selectedTaskId: id })
    // Immediately fetch full detail for the selected task so all steps render instantly
    try {
      const full = normalise(await api.getTask(id))
      set((s) => ({
        tasks: { ...s.tasks, [id]: full },
      }))
    } catch {
      // Silently ignore — refreshTasks will pick it up on next poll
    }
  },

  startPolling: () => {
    if (get()._pollingHandle !== null) return
    get().refreshTasks()
    const handle = setInterval(() => {
      get().refreshTasks()
    }, POLL_INTERVAL_MS)
    set({ _pollingHandle: handle })
  },

  stopPolling: () => {
    const handle = get()._pollingHandle
    if (handle !== null) {
      clearInterval(handle)
      set({ _pollingHandle: null })
    }
  },
}))
