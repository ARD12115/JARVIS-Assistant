import { useEffect, useState, useRef } from 'react'
import { invoke } from '@tauri-apps/api/core'
import { ChatWindow } from './components/ChatWindow'
import { Sidebar } from './components/Sidebar'
import { useChatStore } from './store/chatStore'
import { Menu, X, Sparkles, Bot, Zap, Shield, Mic, Settings } from 'lucide-react'

function App() {
  const [isTauri, setIsTauri] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [showWelcome, setShowWelcome] = useState(true)
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null)
  const sidebarRef = useRef<HTMLDivElement>(null)
  const { sessions, currentSessionId, loadSessions, setCurrentSession } = useChatStore()

  // Check if running in Tauri
  useEffect(() => {
    const checkTauri = async () => {
      try {
        await invoke('send_message', { 
          request: { sessionId: 'health-check', content: '' } 
        })
        setIsTauri(true)
      } catch {
        setIsTauri(false)
      }
    }
    checkTauri()
  }, [])

  useEffect(() => {
    loadSessions()
  }, [loadSessions])

  const handleNewChat = async () => {
    try {
      const sessionId = await invoke('create_session') as string
      setCurrentSession(sessionId)
      setShowWelcome(false)
      showToast('New chat created', 'success')
    } catch (error) {
      showToast('Failed to create chat', 'error')
    }
  }

  const handleSessionSelect = (sessionId: string) => {
    setCurrentSession(sessionId)
    setShowWelcome(false)
    if (sidebarCollapsed) setSidebarCollapsed(false)
  }

  const showToast = (message: string, type: 'success' | 'error') => {
    setToast({ message, type })
    setTimeout(() => setToast(null), 3000)
  }

  const formatSessionTime = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const days = Math.floor(diff / (1000 * 60 * 60 * 24))
    
    if (days === 0) return 'Today'
    if (days === 1) return 'Yesterday'
    if (days < 7) return `${days}d ago`
    return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
  }

  return (
    <div className="app-container relative">
      {/* Animated background */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden" aria-hidden="true">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-jarvis-primary/10 rounded-full blur-3xl animate-float" />
        <div className="absolute bottom-1/4 right-1/4 w-72 h-72 bg-jarvis-secondary/10 rounded-full blur-3xl animate-float" style={{ animationDelay: '-3s' }} />
        <div className="absolute top-1/2 left-1/2 w-64 h-64 bg-jarvis-accent/10 rounded-full blur-3xl animate-float" style={{ animationDelay: '-1.5s' }} />
      </div>

      {/* Toast */}
      {toast && (
        <div className={`fixed bottom-6 right-6 z-50 animate-in scale-in ${toast.type === 'success' ? 'bg-jarvis-success/90' : 'bg-jarvis-error/90'} text-white px-4 py-3 rounded-xl shadow-2xl flex items-center gap-2 backdrop-blur-sm`}>
          {toast.type === 'success' ? <span className="w-5 h-5">✓</span> : <span className="w-5 h-5">✕</span>}
          <span>{toast.message}</span>
        </div>
      )}

      {/* Sidebar */}
      <aside
        ref={sidebarRef}
        className={`sidebar ${sidebarCollapsed ? 'w-16' : 'w-80'} ${sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}`}
        style={{ 
          transition: 'width 0.3s cubic-bezier(0.34, 1.56, 0.64, 1), transform 0.3s ease-out',
          zIndex: 50,
        }}
      >
        {/* Sidebar Header */}
        <div className="flex items-center justify-between p-4 border-b border-jarvis-border/50">
          <div className="flex items-center gap-3">
            <div className="relative">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-jarvis-primary to-jarvis-secondary flex items-center justify-center shadow-lg shadow-jarvis-primary/30">
                <Bot className="w-6 h-6 text-white" />
              </div>
              <div className="absolute -bottom-1 -right-1 w-3 h-3 bg-jarvis-success border-2 border-jarvis-bg rounded-full animate-pulse" />
            </div>
            {!sidebarCollapsed && (
              <div className="overflow-hidden">
                <h1 className="text-xl font-bold text-jarvis-text gradient-text">JARVIS</h1>
                <p className="text-xs text-jarvis-textMuted">AI Assistant</p>
              </div>
            )}
          </div>
          
          <button
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            className="btn-ghost p-2 rounded-xl hover:bg-jarvis-primary/10 text-jarvis-textMuted hover:text-jarvis-primary transition-all duration-200"
            aria-label={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            <X className={`w-5 h-5 transition-transform duration-300 ${sidebarCollapsed ? 'rotate-180' : ''}`} />
          </button>
        </div>

        {/* Sessions */}
        <Sidebar
          sessions={sessions}
          currentSessionId={currentSessionId}
          onSessionSelect={handleSessionSelect}
          onNewChat={handleNewChat}
          collapsed={sidebarCollapsed}
          formatTime={formatSessionTime}
        />

        {/* Footer */}
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-jarvis-border/50">
          <div className="flex items-center gap-3 px-3 py-2 rounded-xl bg-jarvis-primary/5 border border-jarvis-primary/20 group">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-jarvis-primary to-jarvis-secondary flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            {!sidebarCollapsed && (
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-jarvis-text truncate">New Feature</p>
                <p className="text-xs text-jarvis-textMuted truncate">Voice input & streaming</p>
              </div>
            )}
          </div>
        </div>
      </aside>

      {/* Mobile sidebar overlay */}
      {sidebarOpen && sidebarCollapsed && (
        <div 
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Main Content */}
      <main className="main-content relative">
        {/* Top Bar */}
        <header className="flex-shrink-0 px-6 py-4 border-b border-jarvis-border/50 bg-jarvis-surface/50 backdrop-blur-xl flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="lg:hidden btn-ghost p-2 rounded-xl hover:bg-jarvis-primary/10"
              aria-label="Toggle sidebar"
            >
              <Menu className="w-6 h-6" />
            </button>
            <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-xl bg-jarvis-primary/5 border border-jarvis-primary/20">
              <Zap className="w-4 h-4 text-jarvis-primary" />
              <span className="text-sm font-medium text-jarvis-text">NVIDIA NIM Active</span>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            {!isTauri && (
              <div className="has-tooltip px-3 py-1.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-300 text-sm flex items-center gap-1.5">
                <span className="w-2 h-2 bg-amber-400 rounded-full animate-pulse" />
                <span>Browser mode</span>
                <div className="tooltip">Running in browser — Tauri features disabled</div>
              </div>
            )}
            
            <div className="flex items-center gap-1">
              <button className="btn-ghost p-2 rounded-xl hover:bg-jarvis-primary/10" aria-label="Settings">
                <Settings className="w-5 h-5" />
              </button>
              <button className="btn-ghost p-2 rounded-xl hover:bg-jarvis-primary/10" aria-label="Voice">
                <Mic className="w-5 h-5" />
              </button>
              <button className="btn-ghost p-2 rounded-xl hover:bg-jarvis-primary/10" aria-label="Shield">
                <Shield className="w-5 h-5" />
              </button>
            </div>
          </div>
        </header>

        {/* Chat Area */}
        <ChatWindow 
          sessionId={currentSessionId}
          isTauri={isTauri}
          showWelcome={showWelcome && !currentSessionId}
          onNewChat={handleNewChat}
        />
      </main>
    </div>
  )
}

export default App