import { useEffect, useState } from 'react'
import { invoke } from '@tauri-apps/api/core'
import { ChatWindow } from './components/ChatWindow'
import { Sidebar } from './components/Sidebar'
import { useChatStore } from './store/chatStore'
import { Message } from './types'

function App() {
  const [isTauri, setIsTauri] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const { sessions, currentSessionId, loadSessions, setCurrentSession, createSession } = useChatStore()

  useEffect(() => {
    // Check if running in Tauri
    invoke('send_message', { sessionId: 'test', content: 'test' })
      .then(() => setIsTauri(true))
      .catch(() => setIsTauri(false))
  }, [])

  useEffect(() => {
    loadSessions()
  }, [loadSessions])

  const handleNewChat = async () => {
    const sessionId = await invoke('create_session') as string
    setCurrentSession(sessionId)
  }

  const handleSessionSelect = (sessionId: string) => {
    setCurrentSession(sessionId)
  }

  return (
    <div className="h-screen w-full flex overflow-hidden">
      {/* Sidebar */}
      <aside className={`${sidebarOpen ? 'w-80' : 'w-16'} flex-shrink-0 bg-jarvis-surface border-r border-jarvis-border flex flex-col transition-all duration-300`}>
        <div className="p-4 border-b border-jarvis-border flex items-center justify-between">
          <h1 className="text-xl font-bold text-jarvis-primary flex items-center gap-2">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.734-.988-2.386l-.548-.547z" />
            </svg>
            {sidebarOpen && 'JARVIS'}
          </h1>
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="btn-ghost p-2"
            aria-label={sidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={sidebarOpen ? "M11 19l-7-7 7-7m8 14l-7-7 7-7" : "M13 5l7 7-7 7M5 5l7 7-7 7"} />
            </svg>
          </button>
        </div>

        <Sidebar
          sessions={sessions}
          currentSessionId={currentSessionId}
          onSessionSelect={handleSessionSelect}
          onNewChat={handleNewChat}
          collapsed={!sidebarOpen}
        />
      </aside>

      {/* Main Chat Area */}
      <main className="flex-1 flex flex-col min-w-0">
        <ChatWindow 
          sessionId={currentSessionId}
          isTauri={isTauri}
        />
      </main>
    </div>
  )
}

export default App