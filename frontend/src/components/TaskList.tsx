import { useTaskStore } from '../store/taskStore'
import { StatusBadge } from './StatusBadge'

function fmt(iso: string) {
  return new Date(iso).toLocaleString()
}

export function TaskList() {
  const tasks          = useTaskStore((s) => s.tasks)
  const selectedTaskId = useTaskStore((s) => s.selectedTaskId)
  const selectTask     = useTaskStore((s) => s.selectTask)

  const sorted = Object.values(tasks).sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  )

  if (sorted.length === 0) {
    return (
      <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-gray-800 mb-4">Tasks</h2>
        <p className="text-sm text-gray-400 text-center py-8">No tasks yet. Submit one above.</p>
      </div>
    )
  }

  return (
    <div className="bg-white border border-gray-200 rounded-xl shadow-sm flex flex-col overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-100">
        <h2 className="text-lg font-semibold text-gray-800">
          Tasks <span className="ml-1 text-sm font-normal text-gray-400">({sorted.length})</span>
        </h2>
      </div>
      <div className="overflow-y-auto flex-1 divide-y divide-gray-50">
        {sorted.map((task) => {
          const isSelected = task.task_id === selectedTaskId
          return (
            <button
              key={task.task_id}
              onClick={() => selectTask(task.task_id)}
              className={`w-full text-left px-6 py-3 hover:bg-gray-50 transition-colors
                ${isSelected ? 'bg-blue-50 border-l-4 border-blue-500' : 'border-l-4 border-transparent'}`}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-mono text-xs text-gray-500 truncate flex-1">
                  {task.task_id.slice(0, 8)}…
                </span>
                <StatusBadge status={task.status} />
              </div>
              <div className="mt-1 flex items-center justify-between gap-2">
                <span className="text-xs text-gray-600 capitalize">
                  {task.task_type.replace(/_/g, ' ')}
                </span>
                <span className="text-xs text-gray-400">{fmt(task.created_at)}</span>
              </div>
              {task.status === 'COMPLETED' && task.report_available && (
                <div className="mt-1">
                  <span className="text-xs text-green-600 font-medium">📄 Report ready</span>
                </div>
              )}
            </button>
          )
        })}
      </div>
    </div>
  )
}
