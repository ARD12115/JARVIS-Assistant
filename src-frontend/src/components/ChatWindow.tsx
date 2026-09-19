import { useEffect, useRef } from 'react'
import { ChatStreamChunk } from '../types'
import { MessageBubble } from './MessageBubble'
import { InputBar } from './InputBar'
import { useChatStore } from '../store/chatStore'

export function ChatWindow({ sessionId, isTauri }: { sessionId: string | null; isTauri: boolean }) {
  const { messages, updateMessage, isStreaming, setIsStreaming } = useChatStore()
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Listen for Tauri events (streaming chunks)
  useEffect(() => {
    if (!isTauri) return

    let unlisten: (() => void) | null = null

    const setupListener = async () => {
      const { listen } = await import('@tauri-apps/api/event')
      unlisten = await listen<ChatStreamChunk>('chat-stream', (event) => {
        const chunk = event.payload
        const lastMsg = messages[messages.length - 1]
        
        if (lastMsg && lastMsg.role === 'assistant' && lastMsg.isStreaming) {
          if (chunk.content) {
            updateMessage(lastMsg.id, { 
              content: lastMsg.content + chunk.content,
              isStreaming: !chunk.done
            })
          }
          // Tauri emits snake_case: tool_calls
          if (chunk.tool_calls && chunk.tool_calls.length > 0) {
            updateMessage(lastMsg.id, { 
              toolCalls: chunk.tool_calls,
              isStreaming: !chunk.done
            })
          }
          if (chunk.done) {
            updateMessage(lastMsg.id, { isStreaming: false })
            setIsStreaming(false)
          }
        }
      })
    }

    setupListener()

    return () => {
      unlisten?.()
    }
  }, [isTauri, messages, updateMessage, setIsStreaming])

  if (!sessionId) {
    return (
      <div className="flex-1 flex items-center justify-center bg-jarvis-bg">
        <div className="text-center p-8">
          <svg className="w-16 h-16 mx-auto text-jarvis-textMuted mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
          <h2 className="text-2xl font-semibold text-jarvis-text mb-2">Welcome to JARVIS</h2>
          <p className="text-jarvis-textMuted max-w-md mx-auto">
            Select a session from the sidebar or create a new chat to get started.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4" role="log" aria-live="polite">
        {messages.map((message) => (
          <MessageBubble 
            key={message.id} 
            message={message} 
          />
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Streaming Indicator */}
      {isStreaming && (
        <div className="px-6 pb-4 flex items-center gap-2 text-jarvis-textMuted text-sm animate-pulse">
          <span className="w-2 h-2 bg-jarvis-primary rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
          <span className="w-2 h-2 bg-jarvis-primary rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
          <span className="w-2 h-2 bg-jarvis-primary rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
          <span>JARVIS is thinking...</span>
        </div>
      )}

      {/* Input Bar */}
      <InputBar disabled={isStreaming} />
    </div>
  )
}