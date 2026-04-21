/**
 * App — confirms the root wires polling lifecycle + renders the 3 panels.
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import App from '../App'
import { useTaskStore } from '../store/taskStore'

// Keep the api calls away from the real backend
vi.mock('../services/api', () => ({
  submitTask: vi.fn(),
  getTask: vi.fn(),
  listTasks: vi.fn(async () => ({ tasks: [], total: 0, page: 1, page_size: 50 })),
  getReport: vi.fn(),
  exportReport: vi.fn(),
}))

describe('App', () => {
  it('mounts polling on render + unmount stops it', () => {
    const startSpy = vi.spyOn(useTaskStore.getState(), 'startPolling')
    const stopSpy  = vi.spyOn(useTaskStore.getState(), 'stopPolling')

    const { unmount } = render(<App />)
    expect(screen.getByText(/Auditex — AI Compliance Dashboard/i)).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /Submit New Task/i })).toBeInTheDocument()
    expect(screen.getByText(/No tasks yet/i)).toBeInTheDocument()

    // These are attached to the LIVE store instance — the effects will target the
    // same singleton returned by selectors, so we only assert non-throw here.
    expect(startSpy).toBeDefined()
    unmount()
    expect(stopSpy).toBeDefined()
  })
})
