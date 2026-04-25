p = r"C:/Users/v_sen/Documents/Projects/0001_Hack0014_Vertex_Swarm_Tashi/auditex/frontend/src/App.tsx"
src = """
import { useEffect, useState } from 'react'
import { useTaskStore } from './store/taskStore'
import { SubmitTaskForm } from './components/SubmitTaskForm'
import { TaskList } from './components/TaskList'
import { TaskDetail } from './components/TaskDetail'
import { HumanReviewPage } from './components/HumanReview/HumanReviewPage'
import { OversightConfigPage } from './components/HumanReview/OversightConfigPage'

type Tab = 'dashboard' | 'human-review' | 'oversight-config'

export default function App() {
  const [tab, setTab] = useState<Tab>('dashboard')
  const startPolling = useTaskStore((s) => s.startPolling)
  const stopPolling = useTaskStore((s) => s.stopPolling)

  useEffect(() => {
    startPolling()
    return () => stopPolling()
  }, [])

  const tabClass = (active: boolean) =>
    active
      ? 'px-3 py-1.5 rounded-md text-sm font-medium bg-blue-50 text-blue-700'
      : 'px-3 py-1.5 rounded-md text-sm font-medium text-gray-600 hover:text-gray-900 hover:bg-gray-50'

  return (
    <div className='min-h-screen bg-gray-100'>
      <header className='bg-white border-b border-gray-200 px-6 py-3 flex items-center gap-4'>
        <div className='flex items-center gap-3'>
          <div className='w-7 h-7 rounded-lg bg-blue-600 flex items-center justify-center'>
            <span className='text-white font-bold text-xs'>Ax</span>
          </div>
          <span className='font-semibold text-gray-800 text-sm tracking-tight'>Auditex - AI Compliance Dashboard</span>
        </div>
        <nav className='flex items-center gap-1 ml-6'>
          <button data-testid='tab-dashboard' onClick={() => setTab('dashboard')} className={tabClass(tab === 'dashboard')}>Dashboard</button>
          <button data-testid='tab-human-review' onClick={() => setTab('human-review')} className={tabClass(tab === 'human-review')}>Human Review</button>
          <button data-testid='tab-oversight-config' onClick={() => setTab('oversight-config')} className={tabClass(tab === 'oversight-config')}>Oversight Config</button>
        </nav>
      </header>

      <main className='max-w-7xl mx-auto px-4 py-6 space-y-4'>
        {tab === 'dashboard' && (
          <>
            <SubmitTaskForm />
            <div className='grid grid-cols-1 lg:grid-cols-2 gap-4 items-start'>
              <div className='lg:max-h-[70vh] flex flex-col'><TaskList /></div>
              <div className='lg:max-h-[70vh] overflow-y-auto'><TaskDetail /></div>
            </div>
          </>
        )}
        {tab === 'human-review' && <HumanReviewPage />}
        {tab === 'oversight-config' && <OversightConfigPage />}
      </main>
    </div>
  )
}
"""
open(p, 'w', encoding='utf-8').write(src)
print('wrote', p, len(src), 'bytes')
