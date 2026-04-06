import { useEffect } from 'react'
import { useTaskStore } from './store/taskStore'
import { SubmitTaskForm } from './components/SubmitTaskForm'
import { TaskList }       from './components/TaskList'
import { TaskDetail }     from './components/TaskDetail'

export default function App() {
  const startPolling = useTaskStore((s) => s.startPolling)
  const stopPolling  = useTaskStore((s) => s.stopPolling)

  useEffect(() => {
    startPolling()
    return () => stopPolling()
  }, [])

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Nav */}
      <header className="bg-white border-b border-gray-200 px-6 py-3 flex items-center gap-3">
        <div className="w-7 h-7 rounded-lg bg-blue-600 flex items-center justify-center">
          <span className="text-white font-bold text-xs">Ax</span>
        </div>
        <span className="font-semibold text-gray-800 text-sm tracking-tight">
          Auditex — AI Compliance Dashboard
        </span>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6 space-y-4">
        {/* Top: Submit */}
        <SubmitTaskForm />

        {/* Bottom: Task List + Detail side-by-side */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 items-start">
          <div className="lg:max-h-[70vh] flex flex-col">
            <TaskList />
          </div>
          <div className="lg:max-h-[70vh] overflow-y-auto">
            <TaskDetail />
          </div>
        </div>
      </main>
    </div>
  )
}
