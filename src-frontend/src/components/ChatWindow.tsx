import { useEffect, useRef } from 'react'
import { ChatStreamChunk } from '../types'
import { MessageBubble } from './MessageBubble'
import { InputBar } from './InputBar'
import { useChatStore } from '../store/chatStore'
import { Sparkles, Brain, Zap, ExternalLink, X } from 'lucide-react'

const WelcomeScreen = ({ onNewChat }: { onNewChat: () => void }) => (
  <div className="flex-1 flex flex-col">
    <div className="flex-1 flex items-center justify-center p-8">
      <div className="text-center max-w-xl mx-auto animate-in">
        <div className="relative mx-auto mb-8">
          <div className="w-32 h-32 mx-auto rounded-2xl bg-gradient-to-br from-jarvis-primary/20 to-jarvis-secondary/20 flex items-center justify-center mb-6 shadow-xl shadow-jarvis-primary/20">
            <div className="w-20 h-20 rounded-xl bg-gradient-to-br from-jarvis-primary to-jarvis-secondary flex items-center justify-center shadow-lg shadow-jarvis-primary/30">
              <Zap className="w-10 h-10 text-white" />
            </div>
          </div>
          <div className="absolute -top-4 -right-4 w-6 h-6 bg-jarvis-primary/20 rounded-full blur-xl animate-pulse" />
          <div className="absolute -bottom-4 -left-4 w-4 h-4 bg-jarvis-secondary/20 rounded-full blur-xl animate-float" style={{ animationDelay: '-2s' }} />
        </div>
        <h1 className="text-4xl font-bold text-jarvis-text mb-4 gradient-text">Welcome to JARVIS</h1>
        <p className="text-jarvis-textMuted text-lg mb-8 max-w-md mx-auto leading-relaxed">
          Your AI assistant with streaming chat, voice I/O, and powerful tools.
          Built with Tauri, React, and NVIDIA NIM.
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8 max-w-2xl mx-auto">
          {[
            { icon: Sparkles, title: 'Smart Chat', desc: 'Streaming responses with NVIDIA NIM' },
            { icon: Brain, title: 'Tools', desc: 'Web search, files, code, weather' },
            { icon: Zap, title: 'Voice I/O', desc: 'Push-to-talk STT + TTS' },
          ].map((feature, i) => (
            <div key={feature.title} className={"stagger-" + (i + 1) + " p-4 rounded-xl bg-jarvis-surface/50 border border-jarvis-border/50 hover:border-jarvis-primary/30 transition-all duration-300 group"}>
              <div className="w-10 h-10 rounded-xl bg-jarvis-primary/10 flex items-center justify-center mb-3 group-hover:bg-jarvis-primary/20 transition-colors">
                <feature.icon className="w-5 h-5 text-jarvis-primary group-hover:text-jarvis-primaryHover transition-colors" />
              </div>
              <h3 className="font-semibold text-jarvis-text mb-1">{feature.title}</h3>
              <p className="text-sm text-jarvis-textMuted">{feature.desc}</p>
            </div>
          ))}
        </div>
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <button onClick={onNewChat} className="btn-primary group px-8 py-3 text-base">
            <span className="flex items-center gap-2">
              <span>Start New Chat</span>
              <ExternalLink className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </span>
          </button>
        </div>
      </div>
    </div>
  </div>
)

const EmptyState = () => (
  <div className="flex-1 flex items-center justify-center p-8">
    <div className="text-center max-w-md animate-in">
      <div className="w-20 h-20 mx-auto rounded-2xl bg-jarvis-surface/50 border border-jarvis-border/50 flex items-center justify-center mb-6">
        <Sparkles className="w-10 h-10 text-jarvis-textMuted/50" />
      </div>
      <h2 className="text-2xl font-bold text-jarvis-text mb-2">Conversation Started</h2>
      <p className="text-jarvis-textMuted mb-6">Type a message below to begin your conversation with JARVIS.</p>
      <div className="flex flex-wrap items-center justify-center gap-2 text-sm text-jarvis-textMuted">
        <span className="px-3 py-1 bg-jarvis-surface border border-jarvis-border rounded-full">Try: "What's the weather?"</span>
        <span className="px-3 py-1 bg-jarvis-surface border border-jarvis-border rounded-full">Try: "Search for AI news"</span>
        <span className="px-3 py-1 bg-jarvis-surface border border-jarvis-border rounded-full">Try: "Run python code"</span>
      </div>
    </div>
  </div>
)

const StreamingIndicator = ({ isStreaming, setIsStreaming }: {
  isStreaming: boolean
  setIsStreaming: (streaming: boolean) => void
}) => (
  isStreaming && (
    <div className="streaming-indicator mx-6 mb-4 animate-in slide-up">
      <div className="flex items-center gap-3">
        <div className="flex gap-1.5">
          <span className="streaming-dot stagger-1" />
          <span className="streaming-dot stagger-2" />
          <span className="streaming-dot stagger-3" />
        </div>
        <span className="text-sm font-medium">JARVIS is thinking...</span>
        <div className="flex-1" />
        <button onClick={() => setIsStreaming(false)} className="btn-ghost p-1.5 rounded-lg text-jarvis-textMuted hover:text-jarvis-error" aria-label="Stop streaming">
          <X className="w-4 h-4" />
        </button>
      </div>
    </div>
  )
)

export function ChatWindow({ 
  sessionId, 
  isTauri, 
  onNewChat
}: { 
  sessionId: string | null
  isTauri: boolean
  onNewChat?: () => void
}) {
  const { messages, updateMessage, isStreaming, setIsStreaming } = useChatStore()
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

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
            updateMessage(lastMsg.id, { content: lastMsg.content + chunk.content, isStreaming: !chunk.done })
          }
          if (chunk.tool_calls && chunk.tool_calls.length > 0) {
            updateMessage(lastMsg.id, { toolCalls: chunk.tool_calls, isStreaming: !chunk.done })
          }
          if (chunk.done) {
            updateMessage(lastMsg.id, { isStreaming: false })
            setIsStreaming(false)
          }
        }
      })
    }
    setupListener()
    return () => { unlisten?.() }
  }, [isTauri, messages, updateMessage, setIsStreaming])

  // Welcome Screen (no session)
  if (!sessionId) {
    return <WelcomeScreen onNewChat={onNewChat || (() => {})} />
  }

  return (
    <div className="flex-1 flex flex-col">
      {messages.length === 0 && sessionId && <EmptyState />}
      <div className="flex-1 overflow-y-auto p-6 space-y-5" role="log" aria-live="polite">
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}
        <div ref={messagesEndRef} />
      </div>
      <StreamingIndicator isStreaming={isStreaming} setIsStreaming={setIsStreaming} />
      <InputBar disabled={isStreaming} />
    </div>
  )
}

export default ChatWindow