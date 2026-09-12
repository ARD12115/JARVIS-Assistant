import React from 'react'
import { Session } from '../types'
import { Plus, MessageSquare, X, Clock, ChevronRight } from 'lucide-react'

interface SidebarProps {
  sessions: Session[]
  currentSessionId: string | null
  onSessionSelect: (sessionId: string) => void
  onNewChat: () => void
  collapsed: boolean
}

export function Sidebar({ sessions, currentSessionId, onSessionSelect, onNewChat, collapsed }: SidebarProps) {
  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const days = Math.floor(diff / (1000 * 60 * 60 * 24))
    
    if (days === 0) return 'Today'
    if (days === 1) return 'Yesterday'
    if (days < 7) return `${days} days ago`
    return date.toLocaleDateString()
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* New Chat Button */}
      <button
        onClick={onNewChat}
        className="m-3 btn-primary w-full justify-center gap-2"
        aria-label="New chat"
      >
        <Plus className="w-4 h-4" />
        {!collapsed && <span>New Chat</span>}
      </button>

      {/* Sessions List */}
      <div className="flex-1 overflow-y-auto px-2 pb-4 space-y-1">
        {sessions.length === 0 ? (
          !collapsed && (
            <div className="px-3 py-6 text-center text-jarvis-textMuted text-sm">
              No conversations yet
            </div>
          )
        ) : (
          sessions.map((session) => {
            const isActive = session.session_id === currentSessionId
            return (
              <button
                key={session.session_id}
                onClick={() => onSessionSelect(session.session_id)}
                className={`sidebar-item w-full text-left ${isActive ? 'sidebar-item-active' : ''} ${collapsed ? 'justify-center' : ''}`}
                aria-current={isActive}
                title={collapsed ? `${session.preview || 'Session'} (${formatDate(session.started_at)})` : ''}
              >
                <MessageSquare className="w-5 h-5 flex-shrink-0" />
                {!collapsed && (
                  <div className="flex-1 min-w-0 text-left">
                    <p className="text-sm font-medium truncate">
                      {session.preview || 'New conversation'}
                    </p>
                    <div className="flex items-center gap-2 text-xs text-jarvis-textMuted">
                      <Clock className="w-3 h-3" />
                      <span className="truncate">{formatDate(session.started_at)}</span>
                      <span>•</span>
                      <span>{session.turn_count} messages</span>
                    </div>
                  </div>
                )}
              </button>
            )
          })
        )}
      </div>

      {/* Footer */}
      <div className="p-3 border-t border-jarvis-border">
        {!collapsed && (
          <div className="text-xs text-jarvis-textMuted text-center">
            Press <kbd className="px-1.5 py-0.5 bg-jarvis-bg rounded text-jarvis-text font-mono">Ctrl+K</kbd> for command palette
          </div>
        )}
      </div>
    </div>
  )
}