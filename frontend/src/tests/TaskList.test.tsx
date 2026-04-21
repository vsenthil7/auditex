/**
 * TaskList — covers empty state, listing + sort by created_at desc, selection highlight,
 * report-ready badge, click-to-select.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { TaskList } from '../components/TaskList'
import { useTaskStore } from '../store/taskStore'

function resetStore(overrides: Partial<ReturnType<typeof useTaskStore.getState>> = {}) {
  useTaskStore.setState({
    tasks: {},
    selectedTaskId: null,
    loading: false,
    error: null,
    _pollingHandle: null,
    ...overrides,
  })
}

beforeEach(() => {
  resetStore()
  vi.clearAllMocks()
})

describe('TaskList', () => {
  it('renders empty state when no tasks', () => {
    render(<TaskList />)
    expect(screen.getByText(/No tasks yet/i)).toBeInTheDocument()
  })

  it('lists tasks sorted by created_at descending', () => {
    resetStore({
      tasks: {
        old: {
          task_id: 'oldtaskid1', task_type: 'document_review', status: 'COMPLETED',
          created_at: '2026-04-21T08:00:00Z', report_available: false,
        } as any,
        new: {
          task_id: 'newtaskid2', task_type: 'risk_analysis', status: 'EXECUTING',
          created_at: '2026-04-21T10:00:00Z', report_available: false,
        } as any,
      },
    })
    render(<TaskList />)
    // Count shows 2
    expect(screen.getByText(/\(2\)/)).toBeInTheDocument()
    const buttons = screen.getAllByRole('button')
    // Newest first — button[0] must contain newtaskid2 prefix
    expect(buttons[0].textContent).toContain('newtaskid')
    expect(buttons[1].textContent).toContain('oldtaskid')
  })

  it('highlights selected task and fires selectTask on click', () => {
    const selectSpy = vi.fn()
    resetStore({
      selectTask: selectSpy,
      tasks: {
        t1: {
          task_id: 't1', task_type: 'risk_analysis', status: 'EXECUTING',
          created_at: '2026-04-21T10:00:00Z', report_available: false,
        } as any,
      },
    } as any)

    const { container } = render(<TaskList />)
    const btn = screen.getByRole('button')
    expect(btn.className).not.toMatch(/border-blue-500/)

    // Re-render with selected
    resetStore({
      selectedTaskId: 't1',
      selectTask: selectSpy,
      tasks: {
        t1: {
          task_id: 't1', task_type: 'risk_analysis', status: 'EXECUTING',
          created_at: '2026-04-21T10:00:00Z', report_available: false,
        } as any,
      },
    } as any)

    render(<TaskList />)
    // There will now be two renders; grab the most recent rendered button from container
    const selected = container.querySelector('button.border-blue-500')
    // The first render (un-selected) still sits in the previous container — but the second
    // render lives in the document body; assert via a DOM query instead:
    expect(document.querySelector('button.border-blue-500')).toBeTruthy()

    // Click the rendered button to exercise onClick
    fireEvent.click(document.querySelectorAll('button')[0] as HTMLElement)
    expect(selectSpy).toHaveBeenCalledWith('t1')
    // Avoid dead-code warning -- value validated above via document.querySelector
    expect(selected === null || selected instanceof HTMLElement).toBe(true)
  })

  it('shows "Report ready" badge when COMPLETED + report_available', () => {
    resetStore({
      tasks: {
        r1: {
          task_id: 'reportready1', task_type: 'document_review', status: 'COMPLETED',
          created_at: '2026-04-21T10:00:00Z', report_available: true,
        } as any,
      },
    })
    render(<TaskList />)
    expect(screen.getByText(/Report ready/i)).toBeInTheDocument()
  })

  it('does NOT show Report ready when completed but unavailable', () => {
    resetStore({
      tasks: {
        r2: {
          task_id: 'reportwait1', task_type: 'document_review', status: 'COMPLETED',
          created_at: '2026-04-21T10:00:00Z', report_available: false,
        } as any,
      },
    })
    render(<TaskList />)
    expect(screen.queryByText(/Report ready/i)).not.toBeInTheDocument()
  })
})
