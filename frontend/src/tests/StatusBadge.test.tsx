/**
 * StatusBadge — covers all 7 task-status branches + unknown fallback.
 */
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { StatusBadge } from '../components/StatusBadge'

const STATUSES = [
  'QUEUED', 'EXECUTING', 'REVIEWING', 'FINALISING',
  'COMPLETED', 'FAILED', 'ESCALATED',
] as const

describe('StatusBadge', () => {
  it.each(STATUSES)('renders label for %s', (s) => {
    render(<StatusBadge status={s} />)
    expect(screen.getByText(s)).toBeInTheDocument()
  })

  it('applies animate-pulse for in-flight statuses', () => {
    const { container, rerender } = render(<StatusBadge status="EXECUTING" />)
    expect(container.querySelector('.animate-pulse')).toBeInTheDocument()

    rerender(<StatusBadge status="COMPLETED" />)
    expect(container.querySelector('.animate-pulse')).not.toBeInTheDocument()
  })

  it('falls back to QUEUED config for an unknown status', () => {
    // Cast to satisfy TS — runtime fallback is deliberate.
    render(<StatusBadge status={'WAT' as any} />)
    expect(screen.getByText('QUEUED')).toBeInTheDocument()
  })
})
