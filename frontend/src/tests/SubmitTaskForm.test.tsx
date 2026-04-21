/**
 * SubmitTaskForm — covers: rendering, task-type select, criteria toggle
 * (add + remove), validation error, submit calls store, clear-on-success.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { SubmitTaskForm } from '../components/SubmitTaskForm'
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

describe('SubmitTaskForm', () => {
  it('renders with default task type + button', () => {
    render(<SubmitTaskForm />)
    expect(screen.getByRole('heading', { name: /Submit New Task/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Submit Task/i })).toBeInTheDocument()
  })

  it('displays all three task types with humanised labels', () => {
    render(<SubmitTaskForm />)
    const select = screen.getByLabelText(/Task Type/i) as HTMLSelectElement
    const values = Array.from(select.options).map(o => o.value)
    expect(values).toEqual(['document_review', 'risk_analysis', 'contract_check'])
    expect(screen.getByText('Document Review')).toBeInTheDocument()
    expect(screen.getByText('Risk Analysis')).toBeInTheDocument()
    expect(screen.getByText('Contract Check')).toBeInTheDocument()
  })

  it('shows validation error when document is blank and does NOT call the store', async () => {
    const submitSpy = vi.fn()
    resetStore({ submitTask: submitSpy } as any)
    render(<SubmitTaskForm />)
    await userEvent.click(screen.getByRole('button', { name: /Submit Task/i }))
    expect(screen.getByText(/Document content is required/i)).toBeInTheDocument()
    expect(submitSpy).not.toHaveBeenCalled()
  })

  it('does not submit when document is only whitespace', async () => {
    const submitSpy = vi.fn()
    resetStore({ submitTask: submitSpy } as any)
    render(<SubmitTaskForm />)
    const textarea = screen.getByPlaceholderText(/Paste document content/i)
    await userEvent.type(textarea, '   ')
    await userEvent.click(screen.getByRole('button', { name: /Submit Task/i }))
    expect(submitSpy).not.toHaveBeenCalled()
  })

  it('submits with trimmed document + selected criteria; clears fields on success', async () => {
    const submitSpy = vi.fn(async () => {})
    resetStore({ submitTask: submitSpy } as any)
    render(<SubmitTaskForm />)

    const textarea = screen.getByPlaceholderText(/Paste document content/i) as HTMLTextAreaElement
    await userEvent.type(textarea, '  Some document body  ')

    // Toggle two criteria on
    await userEvent.click(screen.getByLabelText('Completeness'))
    await userEvent.click(screen.getByLabelText('Risk Assessment'))
    // Toggle Completeness off again
    await userEvent.click(screen.getByLabelText('Completeness'))

    // Change task type
    fireEvent.change(screen.getByLabelText(/Task Type/i), { target: { value: 'contract_check' } })

    await userEvent.click(screen.getByRole('button', { name: /Submit Task/i }))

    expect(submitSpy).toHaveBeenCalledTimes(1)
    expect(submitSpy).toHaveBeenCalledWith({
      task_type: 'contract_check',
      document: 'Some document body',
      review_criteria: ['risk_assessment'],
    })
    expect(textarea.value).toBe('')
    expect((screen.getByLabelText('Risk Assessment') as HTMLInputElement).checked).toBe(false)
  })

  it('button shows "Submitting…" when loading', () => {
    resetStore({ loading: true })
    render(<SubmitTaskForm />)
    const button = screen.getByRole('button', { name: /Submitting/i }) as HTMLButtonElement
    expect(button).toBeDisabled()
  })
})
