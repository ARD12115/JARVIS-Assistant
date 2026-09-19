import { Session } from '../types'
import { Plus, MessageSquare, Clock, Search, Archive, FolderOpen } from 'lucide-react'
import { useState } from 'react'

interface SidebarProps {
  sessions: Session[]
  currentSessionId: string | null
  onSessionSelect: (sessionId: string) => void
  onNewChat: () => void
  collapsed: boolean
  formatTime: (dateString: string) => string
}

export function Sidebar({ sessions, currentSessionId, onSessionSelect, onNewChat, collapsed, formatTime }: SidebarProps) {
  const [searchQuery, setSearchQuery] = useState('')

  const filteredSessions = sessions.filter(session => {
    const matchesSearch = session.preview.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         session.session_id.toLowerCase().includes(searchQuery.toLowerCase())
    return matchesSearch
  })

  const newChatButtonClass = `btn-primary w-full justify-center gap-3 ${collapsed ? 'px-3' : ''} group`
  const newChatButtonDivClass = `p-3 ${collapsed ? 'px-2' : ''}`

  const renderSessions = () => {
    if (filteredSessions.length === 0) {
      return (
        !collapsed && (
          <div className="px-3 py-8 text-center text-jarvis-textMuted">
            <MessageSquare className="w-12 h-12 mx-auto mb-3 text-jarvis-textMuted/30" />
            <p className="text-sm font-medium">No conversations yet</p>
            <p className="text-xs text-jarvis-textSubtle mt-1">Start a new chat to begin</p>
          </div>
        )
      )
    }

    return (
      filteredSessions.map((session) => {
        const isActive = session.session_id === currentSessionId
        const sessionItemClass = `session-item ${isActive ? 'session-item-active' : ''} ${collapsed ? 'justify-center px-2' : ''} relative group`
        const messageSquareClass = `w-5 h-5 flex-shrink-0 ${isActive ? 'text-jarvis-primary' : 'text-jarvis-textMuted'} group-hover:text-jarvis-primary transition-colors`
        const title = collapsed ? `${session.preview} (${formatTime(session.started_at)})` : ''

        return (
          <button
            key={session.session_id}
            onClick={() => onSessionSelect(session.session_id)}
            className={sessionItemClass}
            aria-current={isActive}
            title={title}
          >
            <MessageSquare className={messageSquareClass} />
            {!collapsed && (
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate group-hover:text-jarvis-text transition-colors">
                  {session.preview || 'New conversation'}
                </p>
                <div className="flex items-center gap-2 text-xs text-jarvis-textMuted mt-0.5">
                  <Clock className="w-3 h-3" />
                  <span className="truncate">{formatTime(session.started_at)}</span>
                  <span className="hidden sm:inline">\u2022</span>
                  <span className="hidden sm:inline">{session.turn_count} msgs</span>
                </div>
              </div>
            )}
          </button>
        )
      })
    )
  }

  const renderFooter = () => {
    if (collapsed) return null

    return (
      <div className="p-3 border-t border-jarvis-border/50 space-y-2">
        <button className="sidebar-item w-full justify-center gap-2 text-jarvis-textMuted hover:text-jarvis-text hover:bg-jarvis-surface/50">
          <Archive className="w-5 h-5" />
          <span>Archive</span>
        </button>
        <button className="sidebar-item w-full justify-center gap-2 text-jarvis-textMuted hover:text-jarvis-text hover:bg-jarvis-surface/50">
          <FolderOpen className="w-5 h-5" />
          <span>Export Data</span>
        </button>
      </div>
    )
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden min-h-0">
      <div className={newChatButtonDivClass}>
        <button
          onClick={onNewChat}
          className={newChatButtonClass}
          aria-label="New chat"
        >
          <Plus className="w-5 h-5" />
          {!collapsed && (
            <span className="font-medium">New Chat</span>
          )}
        </button>
      </div>

      {!collapsed && (
        <div className="px-3 pb-2">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-jarvis-textMuted" />
            <input
              type="text"
              placeholder="Search conversations..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="input pl-10 py-2 text-sm"
            />
          </div>
        </div>
      )}

      <div className="flex-1 overflow-y-auto px-2 pb-4 space-y-1">
        {renderSessions()}
        {renderFooter()}
      </div>
    </div>
  )
}