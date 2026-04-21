/**
 * Tests for src/store/taskStore.ts
 * Covers submitTask, refreshTasks (all enrichment branches), selectTask, start/stopPolling, normalise defaults.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'

// Mock the api module. We'll override per-test.
vi.mock('../services/api', () => ({
  submitTask: vi.fn(),
  getTask: vi.fn(),
  listTasks: vi.fn(),
  getReport: vi.fn(),
  exportReport: vi.fn(),
}))

import * as api from '../services/api'
import { useTaskStore } from '../store/taskStore'

// Helper — reset the zustand store between tests
function resetStore() {
  useTaskStore.setState({
    tasks: {},
    selectedTaskId: null,
    loading: false,
    error: null,
    _pollingHandle: null,
  })
}

beforeEach(() => {
  resetStore()
  vi.clearAllMocks()
  vi.useFakeTimers()
})

afterEach(() => {
  useTaskStore.getState().stopPolling()
  vi.useRealTimers()
})

describe('submitTask', () => {
  it('adds task and selects it; triggers a refreshTasks', async () => {
    vi.mocked(api.submitTask).mockResolvedValue({
      task_id: 'new1',
      task_type: 'document_review',
      status: 'QUEUED',
      created_at: '2026-04-21T10:00:00Z',
      report_available: false,
    } as any)
    vi.mocked(api.listTasks).mockResolvedValue({
      tasks: [], total: 0, page: 1, page_size: 100,
    } as any)

    await useTaskStore.getState().submitTask({
      task_type: 'document_review', document: 'doc', review_criteria: [],
    })

    const s = useTaskStore.getState()
    expect(s.tasks['new1']).toBeDefined()
    expect(s.tasks['new1'].status).toBe('QUEUED')
    expect(s.selectedTaskId).toBe('new1')
    expect(s.loading).toBe(false)
    expect(api.submitTask).toHaveBeenCalled()
  })

  it('sets error and keeps loading false on failure', async () => {
    vi.mocked(api.submitTask).mockRejectedValue(new Error('boom'))
    await useTaskStore.getState().submitTask({
      task_type: 'x', document: 'y', review_criteria: [],
    })
    const s = useTaskStore.getState()
    expect(s.error).toContain('boom')
    expect(s.loading).toBe(false)
  })

  it('normalise supplies defaults when fields are missing', async () => {
    vi.mocked(api.submitTask).mockResolvedValue({ task_id: 'bare' } as any)
    vi.mocked(api.listTasks).mockResolvedValue({ tasks: [] } as any)
    await useTaskStore.getState().submitTask({
      task_type: 'x', document: 'y', review_criteria: [],
    })
    const t = useTaskStore.getState().tasks['bare']
    expect(t.task_type).toBe('unknown')
    expect(t.status).toBe('QUEUED')
    expect(t.report_available).toBe(false)
    expect(t.executor).toBeNull()
    expect(t.review).toBeNull()
    expect(t.vertex).toBeNull()
    expect(typeof t.created_at).toBe('string')
  })
})

describe('refreshTasks enrichment', () => {
  it('fetches full detail for the selected task', async () => {
    useTaskStore.setState({ selectedTaskId: 'sel' })
    vi.mocked(api.listTasks).mockResolvedValue({
      tasks: [{ task_id: 'sel', status: 'COMPLETED', report_available: true } as any],
    } as any)
    vi.mocked(api.getTask).mockResolvedValue({
      task_id: 'sel', status: 'COMPLETED', report_available: true,
      executor: { model: 'claude' } as any,
    } as any)

    await useTaskStore.getState().refreshTasks()
    expect(api.getTask).toHaveBeenCalledWith('sel')
    expect(useTaskStore.getState().tasks['sel'].executor).toEqual({ model: 'claude' })
  })

  it('fetches full detail for active tasks (EXECUTING/REVIEWING/FINALISING)', async () => {
    vi.mocked(api.listTasks).mockResolvedValue({
      tasks: [
        { task_id: 'a', status: 'EXECUTING', report_available: false } as any,
        { task_id: 'b', status: 'REVIEWING', report_available: false } as any,
        { task_id: 'c', status: 'FINALISING', report_available: false } as any,
      ],
    } as any)
    vi.mocked(api.getTask).mockImplementation(async (id: string) => ({
      task_id: id, status: 'COMPLETED', report_available: true, executor: { id } as any,
    } as any))

    await useTaskStore.getState().refreshTasks()
    expect(api.getTask).toHaveBeenCalledTimes(3)
  })

  it('fetches full detail for COMPLETED without report_available', async () => {
    vi.mocked(api.listTasks).mockResolvedValue({
      tasks: [{ task_id: 'c1', status: 'COMPLETED', report_available: false } as any],
    } as any)
    vi.mocked(api.getTask).mockResolvedValue({
      task_id: 'c1', status: 'COMPLETED', report_available: false,
    } as any)
    await useTaskStore.getState().refreshTasks()
    expect(api.getTask).toHaveBeenCalledWith('c1')
  })

  it('falls back to list data when getTask throws', async () => {
    useTaskStore.setState({ selectedTaskId: 'err' })
    vi.mocked(api.listTasks).mockResolvedValue({
      tasks: [{ task_id: 'err', status: 'COMPLETED', report_available: true } as any],
    } as any)
    vi.mocked(api.getTask).mockRejectedValue(new Error('network down'))
    await useTaskStore.getState().refreshTasks()
    expect(useTaskStore.getState().tasks['err']).toBeDefined()
    expect(useTaskStore.getState().tasks['err'].status).toBe('COMPLETED')
  })

  it('preserves existing enriched data on COMPLETED+report tasks that are NOT selected', async () => {
    useTaskStore.setState({
      tasks: {
        keep: {
          task_id: 'keep', task_type: 'document_review', status: 'COMPLETED',
          created_at: '2026-04-21T00:00:00Z', report_available: true,
          executor: { model: 'claude-existing' } as any, review: null, vertex: null,
        } as any,
      },
    })
    vi.mocked(api.listTasks).mockResolvedValue({
      tasks: [{ task_id: 'keep', status: 'COMPLETED', report_available: true } as any],
    } as any)
    await useTaskStore.getState().refreshTasks()
    expect(api.getTask).not.toHaveBeenCalled()
    expect(useTaskStore.getState().tasks['keep'].executor).toEqual({ model: 'claude-existing' })
  })

  it('handles a stale COMPLETED task with no prior enriched data', async () => {
    vi.mocked(api.listTasks).mockResolvedValue({
      tasks: [{ task_id: 'plain', status: 'COMPLETED', report_available: true } as any],
    } as any)
    await useTaskStore.getState().refreshTasks()
    expect(api.getTask).not.toHaveBeenCalled()
    expect(useTaskStore.getState().tasks['plain']).toBeDefined()
  })

  it('accepts missing `tasks` field on list response', async () => {
    vi.mocked(api.listTasks).mockResolvedValue({} as any)
    await useTaskStore.getState().refreshTasks()
    expect(useTaskStore.getState().tasks).toEqual({})
  })

  it('sets error when listTasks throws', async () => {
    vi.mocked(api.listTasks).mockRejectedValue(new Error('nope'))
    await useTaskStore.getState().refreshTasks()
    expect(useTaskStore.getState().error).toContain('nope')
  })
})

describe('selectTask', () => {
  it('sets selectedTaskId and fetches full detail', async () => {
    vi.mocked(api.getTask).mockResolvedValue({
      task_id: 'pick', status: 'COMPLETED', report_available: true,
      executor: { model: 'x' } as any,
    } as any)
    await useTaskStore.getState().selectTask('pick')
    expect(useTaskStore.getState().selectedTaskId).toBe('pick')
    expect(useTaskStore.getState().tasks['pick']?.executor).toEqual({ model: 'x' })
  })

  it('silently ignores getTask failure', async () => {
    vi.mocked(api.getTask).mockRejectedValue(new Error('nope'))
    await useTaskStore.getState().selectTask('picky')
    expect(useTaskStore.getState().selectedTaskId).toBe('picky')
    // Did not populate
    expect(useTaskStore.getState().tasks['picky']).toBeUndefined()
  })
})

describe('polling lifecycle', () => {
  it('startPolling schedules refreshTasks every 3s; stopPolling clears handle', async () => {
    vi.mocked(api.listTasks).mockResolvedValue({ tasks: [] } as any)
    useTaskStore.getState().startPolling()
    // Initial fire runs synchronously via the call inside startPolling
    expect(api.listTasks).toHaveBeenCalledTimes(1)

    vi.advanceTimersByTime(3001)
    await Promise.resolve() // let the scheduled microtask finish
    expect(api.listTasks).toHaveBeenCalledTimes(2)

    useTaskStore.getState().stopPolling()
    vi.advanceTimersByTime(10_000)
    // No additional calls after stop
    expect(api.listTasks).toHaveBeenCalledTimes(2)
  })

  it('startPolling is idempotent -- second call is a no-op', async () => {
    vi.mocked(api.listTasks).mockResolvedValue({ tasks: [] } as any)
    useTaskStore.getState().startPolling()
    const handle = useTaskStore.getState()._pollingHandle
    useTaskStore.getState().startPolling()
    expect(useTaskStore.getState()._pollingHandle).toBe(handle)
  })

  it('stopPolling is safe when no handle exists', () => {
    // No throw, no-op
    expect(() => useTaskStore.getState().stopPolling()).not.toThrow()
  })
})
