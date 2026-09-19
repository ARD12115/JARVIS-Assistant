import { create } from 'zustand'
import { invoke } from '@tauri-apps/api/core'
import { Message, Session } from '../types'

interface ChatState {
  // Messages
  messages: Message[]
  addMessage: (message: Message) => void
  updateMessage: (id: string, updates: Partial<Message>) => void
  clearMessages: () => void
  
  // Streaming state
  isStreaming: boolean
  setIsStreaming: (streaming: boolean) => void
  
  // Sessions
  sessions: Session[]
  currentSessionId: string | null
  loadSessions: () => Promise<void>
  setCurrentSession: (sessionId: string) => void
  createSession: () => Promise<string>
  
  // Send message
  sendMessage: (content: string) => Promise<void>
  
  // Voice
  isRecording: boolean
  setIsRecording: (recording: boolean) => void
  startVoiceInput: () => Promise<void>
  stopVoiceInput: () => Promise<void>
}

export const useChatStore = create<ChatState>((set, get) => ({
  // Messages
  messages: [],
  addMessage: (message) => set((state) => ({ messages: [...state.messages, message] })),
  updateMessage: (id, updates) => set((state) => ({
    messages: state.messages.map((m) => m.id === id ? { ...m, ...updates } : m)
  })),
  clearMessages: () => set({ messages: [] }),
  
  // Streaming
  isStreaming: false,
  setIsStreaming: (streaming) => set({ isStreaming: streaming }),
  
  // Sessions
  sessions: [],
  currentSessionId: null,
  loadSessions: async () => {
    try {
      const sessions = await invoke('list_sessions') as Session[]
      set({ sessions })
      if (sessions.length > 0 && !get().currentSessionId) {
        set({ currentSessionId: sessions[0].session_id })
        // Load history for first session
        const history = await invoke('get_history', { sessionId: sessions[0].session_id }) as Message[]
        set({ messages: history })
      }
    } catch (error) {
      console.error('Failed to load sessions:', error)
    }
  },
  setCurrentSession: async (sessionId) => {
    set({ currentSessionId: sessionId, messages: [], isStreaming: false })
    try {
      const history = await invoke('get_history', { sessionId }) as Message[]
      set({ messages: history })
    } catch (error) {
      console.error('Failed to load history:', error)
    }
  },
  createSession: async () => {
    try {
      const sessionId = await invoke('new_session') as string
      set({ currentSessionId: sessionId, messages: [] })
      // Refresh sessions list
      get().loadSessions()
      return sessionId
    } catch (error) {
      console.error('Failed to create session:', error)
      throw error
    }
  },
  
  // Send message - triggers Tauri command which emits chat-stream events
  sendMessage: async (content) => {
    const { currentSessionId, addMessage, updateMessage, setIsStreaming } = get()
    if (!currentSessionId || !content.trim()) return
    
    // Add user message
    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content: content.trim(),
      timestamp: Date.now(),
    }
    addMessage(userMessage)
    setIsStreaming(true)
    
    // Add placeholder assistant message
    const assistantId = crypto.randomUUID()
    const assistantMessage: Message = {
      id: assistantId,
      role: 'assistant',
      content: '',
      timestamp: Date.now(),
      isStreaming: true,
    }
    addMessage(assistantMessage)
    
    try {
      // Invoke Tauri command - this starts the stream and emits 'chat-stream' events
      // The command expects a `request` parameter matching the Rust ChatRequest struct
      await invoke('send_message', { 
        request: {  // Tauri expects the parameter name to match the Rust function parameter
          session_id: currentSessionId,
          content: content.trim()
        }
      })
    } catch (error) {
      console.error('Failed to send message:', error)
      updateMessage(assistantId, { 
        content: `Failed to send message: ${error}`, 
        isStreaming: false 
      })
      setIsStreaming(false)
    }
    // Note: Streaming completion handled by chat-stream event listener in ChatWindow
    // setIsStreaming(false) is called there when chunk.done === true
  },
  
  // Voice
  isRecording: false,
  setIsRecording: (recording) => set({ isRecording: recording }),
  startVoiceInput: async () => {
    set({ isRecording: true })
    // Voice recording is handled by the InputBar component using MediaRecorder
    // This just sets the recording state; actual STT happens on stop
  },
  stopVoiceInput: async () => {
    try {
      set({ isRecording: false })
      // Voice input stopped - the InputBar handles sending audio to voice_stt
    } catch (error) {
      console.error('Failed to stop voice recording:', error)
    } finally {
      set({ isRecording: false })
    }
  },
}))