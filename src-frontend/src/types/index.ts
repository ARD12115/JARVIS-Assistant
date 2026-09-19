export interface Message {
  id: string
  role: 'user' | 'assistant' | 'tool' | 'system'
  content: string
  toolCalls?: ToolCall[]
  toolCallId?: string
  timestamp: number
  isStreaming?: boolean
}

export interface ToolCall {
  id: string
  type: 'function'
  function: {
    name: string
    arguments: string
  }
}

export interface ToolResult {
  success: boolean
  data?: any
  error?: string
}

export interface Session {
  session_id: string
  started_at: string
  turn_count: number
  preview: string
}

export interface ChatStreamChunk {
  content: string
  done: boolean
  tool_calls?: ToolCall[]  // Tauri sends snake_case from Rust
}