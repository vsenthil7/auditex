import type { TaskStatus } from '../types'

const CONFIG: Record<
  TaskStatus,
  { label: string; classes: string; pulse: boolean }
> = {
  QUEUED:     { label: 'QUEUED',     classes: 'bg-gray-100 text-gray-600',    pulse: false },
  EXECUTING:  { label: 'EXECUTING',  classes: 'bg-blue-100 text-blue-700',    pulse: true  },
  REVIEWING:  { label: 'REVIEWING',  classes: 'bg-purple-100 text-purple-700',pulse: true  },
  FINALISING: { label: 'FINALISING', classes: 'bg-amber-100 text-amber-700',  pulse: true  },
  COMPLETED:  { label: 'COMPLETED',  classes: 'bg-green-100 text-green-700',  pulse: false },
  FAILED:     { label: 'FAILED',     classes: 'bg-red-100 text-red-700',      pulse: false },
  ESCALATED:  { label: 'ESCALATED',  classes: 'bg-orange-100 text-orange-700',pulse: false },
}

interface Props {
  status: TaskStatus
}

export function StatusBadge({ status }: Props) {
  const cfg = CONFIG[status] ?? CONFIG['QUEUED']
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold
        ${cfg.classes} ${cfg.pulse ? 'animate-pulse' : ''}`}
    >
      {cfg.label}
    </span>
  )
}
