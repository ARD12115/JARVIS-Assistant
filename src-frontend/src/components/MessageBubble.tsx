import React from 'react'
import ReactMarkdown from 'react-markdown'
import { remarkGfm } from 'remark-gfm'
import rehypeHighlight from 'rehype-highlight'
import { Message, ToolCall, ToolResult } from '../types'
import { ToolResultCard } from './ToolResultCard'
import { Copy, Terminal, ChevronDown, ChevronUp } from 'lucide-react'
import { useState } from 'react'

interface MessageBubbleProps {
  message: Message
}

const codeBlockComponent = ({ children, ...props }: any) => {
  const [copied, setCopied] = useState(false)
  const [expanded, setExpanded] = useState(false)
  const code = typeof children === 'string' ? children : children.props?.children || ''
  const language = props.className?.replace('language-', '') || ''

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="relative group overflow-hidden rounded-lg bg-jarvis-bg border border-jarvis-border max-h-[300px]">
      <div className="flex items-center justify-between px-3 py-2 bg-jarvis-surface border-b border-jarvis-border">
        <span className="text-xs text-jarvis-textMuted font-mono">{language || 'text'}</span>
        <div className="flex items-center gap-2">
          <button
            onClick={handleCopy}
            className="btn-ghost p-1.5 hover:bg-jarvis-surfaceHover transition-colors"
            aria-label={copied ? 'Copied!' : 'Copy code'}
          >
            {copied ? (
              <svg className="w-4 h-4 text-jarvis-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            ) : (
              <Copy className="w-4 h-4" />
            )}
          </button>
          <button
            onClick={() => setExpanded(!expanded)}
            className="btn-ghost p-1.5 hover:bg-jarvis-surfaceHover transition-colors"
            aria-label={expanded ? 'Collapse' : 'Expand'}
          >
            {expanded ? (
              <ChevronUp className="w-4 h-4" />
            ) : (
              <ChevronDown className="w-4 h-4" />
            )}
          </button>
        </div>
      </div>
      <pre className={`p-4 overflow-x-auto font-mono text-sm ${!expanded ? 'max-h-[300px]' : 'max-h-none'}`}>
        <code className={props.className}>{code}</code>
      </pre>
    </div>
  )
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user'
  const isAssistant = message.role === 'assistant'
  const isTool = message.role === 'tool'

  const timeString = new Date(message.timestamp).toLocaleTimeString([], { 
    hour: '2-digit', 
    minute: '2-digit' 
  })

  if (isTool) {
    return (
      <div className={`flex gap-3 animate-in ${isUser ? 'justify-end' : 'justify-start'}`}>
        <div className="max-w-[85%]">
          <ToolResultCard 
            toolCall={{ id: message.toolCallId || '', type: 'function', function: { name: 'tool', arguments: '{}' }}} 
            result={{ success: true, data: message.content }} 
          />
        </div>
      </div>
    )
  }

  return (
    <div className={`flex gap-3 animate-in ${isUser ? 'justify-end' : 'justify-start'}`}>
      {!isUser && (
        <div className="w-8 h-8 rounded-full bg-jarvis-primary/20 flex items-center justify-center flex-shrink-0 mt-1">
          <svg className="w-5 h-5 text-jarvis-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.734-.988-2.386l-.548-.547z" />
          </svg>
        </div>
      )}
      
      <div className={`max-w-[75%] ${isUser ? 'order-2' : 'order-1'}`}>
        <div className={`relative p-4 rounded-2xl ${
          isUser 
            ? 'bg-jarvis-userMsg rounded-tr-none text-white' 
            : 'bg-jarvis-assistantMsg rounded-tl-none border border-jarvis-border text-jarvis-text'
        }`}>
          <ReactMarkdown
            components={{
              code: codeBlockComponent,
              pre: ({ children }) => children, // Handled by code component
            }}
            remarkPlugins={[remarkGfm]}
            rehypePlugins={[[rehypeHighlight, { ignoreMissing: true }]]}
          >
            {message.content}
          </ReactMarkdown>

          {/* Tool Calls */}
          {message.toolCalls && message.toolCalls.length > 0 && (
            <div className="mt-3 space-y-2">
              {message.toolCalls.map((tc) => (
                <ToolResultCard 
                  key={tc.id} 
                  toolCall={tc} 
                  result={null}
                  isPending={message.isStreaming}
                />
              ))}
            </div>
          )}

          {/* Streaming cursor */}
          {message.isStreaming && (
            <span className="inline-block w-1 h-5 bg-jarvis-primary animate-pulse ml-0.5 align-bottom" />
          )}
        </div>

        <div className={`flex items-center gap-2 mt-1.5 px-1 ${isUser ? 'justify-end' : ''}`}>
          <span className="text-xs text-jarvis-textMuted">{timeString}</span>
          {isAssistant && (
            <button className="btn-ghost p-1.5 hover:bg-jarvis-surfaceHover transition-colors text-jarvis-textMuted" aria-label="Copy response">
              <Copy className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {isUser && (
        <div className="w-8 h-8 rounded-full bg-jarvis-primary flex items-center justify-center flex-shrink-0 mt-1">
          <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
          </svg>
        </div>
      )}
    </div>
  )
}