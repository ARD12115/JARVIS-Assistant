import React, { useRef, useState, useEffect } from 'react'
import { Send, Mic, MicOff, Paperclip, ArrowUp } from 'lucide-react'
import { useChatStore } from '../store/chatStore'

export function InputBar({ sessionId, disabled }: { sessionId: string; disabled: boolean }) {
  const { sendMessage, isRecording, setIsRecording, startVoiceInput, stopVoiceInput } = useChatStore()
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const [value, setValue] = useState('')
  const [height, setHeight] = useState(48)

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      const newHeight = Math.min(textareaRef.current.scrollHeight, 200)
      setHeight(newHeight)
      textareaRef.current.style.height = `${newHeight}px`
    }
  }, [value])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!value.trim() || disabled) return
    sendMessage(value.trim())
    setValue('')
    setHeight(48)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  const handleVoiceToggle = async () => {
    if (isRecording) {
      await stopVoiceInput()
    } else {
      await startVoiceInput()
    }
  }

  return (
    <form onSubmit={handleSubmit} className="p-4 border-t border-jarvis-border bg-jarvis-surface/50 backdrop-blur-sm">
      <div className="flex items-end gap-3">
        {/* Voice Button */}
        <button
          type="button"
          onClick={handleVoiceToggle}
          disabled={disabled}
          className={`btn-ghost p-2.5 rounded-xl transition-all duration-200 ${
            isRecording 
              ? 'bg-red-500/20 text-red-400 animate-pulse ring-2 ring-red-500/30' 
              : 'text-jarvis-textMuted hover:text-jarvis-primary hover:bg-jarvis-primary/10'
          }`}
          aria-label={isRecording ? 'Stop recording' : 'Start voice input'}
          aria-pressed={isRecording}
        >
          {isRecording ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
        </button>

        {/* Text Input */}
        <div className="flex-1 relative">
          <textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={disabled ? 'JARVIS is thinking...' : 'Message JARVIS...'}
            disabled={disabled}
            rows={1}
            className="input resize-none pr-12 min-h-[48px] max-h-[200px]"
            style={{ height: `${height}px` }}
            aria-label="Message input"
          />
        </div>

        {/* Send Button */}
        <button
          type="submit"
          disabled={!value.trim() || disabled}
          className={`btn-primary p-2.5 rounded-xl transition-all duration-200 ${
            !value.trim() || disabled ? 'opacity-50 cursor-not-allowed' : 'hover:scale-105'
          }`}
          aria-label="Send message"
        >
          <ArrowUp className="w-5 h-5" />
        </button>
      </div>
    </form>
  )
}