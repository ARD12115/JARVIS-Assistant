import { useRef, useState, useEffect, useCallback } from 'react'
import { Mic, MicOff, Send, Paperclip, Smile, ArrowUpRight, RotateCcw, X } from 'lucide-react'
import { useChatStore } from '../store/chatStore'

export function InputBar({ disabled }: { disabled: boolean }) {
  const { sendMessage, isRecording, startVoiceInput, stopVoiceInput } = useChatStore()
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const [value, setValue] = useState('')
  const [height, setHeight] = useState(48)
  const [showAttachMenu, setShowAttachMenu] = useState(false)
  const attachMenuRef = useRef<HTMLDivElement>(null)

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      const newHeight = Math.min(textareaRef.current.scrollHeight, 200)
      setHeight(newHeight)
      textareaRef.current.style.height = `${newHeight}px`
    }
  }, [value])

  // Close attach menu on outside click
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (attachMenuRef.current && !attachMenuRef.current.contains(event.target as Node)) {
        setShowAttachMenu(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleSubmit = useCallback((e: React.FormEvent) => {
    e.preventDefault()
    if (!value.trim() || disabled) return
    sendMessage(value.trim())
    setValue('')
    setHeight(48)
  }, [value, disabled, sendMessage])

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
    if (e.key === 'Escape' && showAttachMenu) {
      setShowAttachMenu(false)
    }
  }, [handleSubmit, showAttachMenu])

  const handleVoiceToggle = async () => {
    if (isRecording) {
      await stopVoiceInput()
    } else {
      await startVoiceInput()
    }
  }, [isRecording, startVoiceInput, stopVoiceInput]

  const handleAttachClick = (type: string) => {
    setShowAttachMenu(false)
    // TODO: Implement file attachment, image upload, etc.
    console.log('Attach:', type)
  }

  const isEmpty = !value.trim()

  return (
    <form onSubmit={handleSubmit} className="input-area relative">
      {/* Attach Menu Dropdown */}
      {showAttachMenu && (
        <div 
          ref={attachMenuRef}
          className="absolute bottom-full left-4 right-4 mb-2 animate-in scale-in"
          style={{ transformOrigin: 'bottom left' }}
        >
          <div className="bg-jarvis-surface border border-jarvis-border rounded-2xl p-2 shadow-2xl">
            <div className="grid grid-cols-3 gap-1">
              {[
                { icon: Paperclip, label: 'File', action: () => handleAttachClick('file') },
                { icon: Smile, label: 'Emoji', action: () => handleAttachClick('emoji') },
                { icon: RotateCcw, label: 'Code', action: () => handleAttachClick('code') },
              ].map((item, i) => (
                <button
                  key={item.label}
                  onClick={item.action}
                  className="col-span-1 p-3 rounded-xl bg-jarvis-bg/50 border border-jarvis-border/50 hover:bg-jarvis-primary/10 hover:border-jarvis-primary/30 transition-all duration-200 flex flex-col items-center gap-2 group"
                >
                  <item.icon className="w-5 h-5 text-jarvis-textMuted group-hover:text-jarvis-primary transition-colors" />
                  <span className="text-xs text-jarvis-textMuted group-hover:text-jarvis-text transition-colors">{item.label}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Main Input Bar */}
      <div className="flex items-end gap-3">
        {/* Attach Button */}
        <button
          type="button"
          onClick={() => setShowAttachMenu(!showAttachMenu)}
          disabled={disabled}
          className={`btn-ghost p-2.5 rounded-xl transition-all duration-200 ${disabled ? 'opacity-50 cursor-not-allowed' : 'hover:bg-jarvis-primary/10 text-jarvis-textMuted hover:text-jarvis-primary'}`}
          aria-label={showAttachMenu ? 'Close attachments' : 'Attach file'}
          aria-expanded={showAttachMenu}
        >
          <Paperclip className={`w-5 h-5 transition-transform duration-200 ${showAttachMenu ? 'rotate-45' : ''}`} />
        </button>

        {/* Text Input */}
        <div className="flex-1 relative">
          <div className="relative">
            <textarea
              ref={textareaRef}
              value={value}
              onChange={(e) => setValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={disabled ? 'JARVIS is thinking...' : 'Message JARVIS... (Shift+Enter for new line)'}
              disabled={disabled}
              rows={1}
              className={`textarea pr-16 ${disabled ? 'opacity-60' : ''}`}
              style={{ height: `${height}px` }}
              aria-label="Message input"
            />
            {/* Character count when typing */}
            {value.length > 0 && (
              <div className="absolute bottom-1 right-2 text-xs text-jarvis-textSubtle pointer-events-none">
                {value.length}/4000
              </div>
            )}
          </div>
        </div>

        {/* Voice + Send Buttons */}
        <div className="flex items-center gap-2">
          {/* Voice Button */}
          <button
            type="button"
            onClick={handleVoiceToggle}
            disabled={disabled}
            className={`btn-icon transition-all duration-300 ${isRecording 
              ? 'bg-jarvis-recording/20 text-jarvis-recording ring-2 ring-jarvis-recording/30 animate-pulse' 
              : 'text-jarvis-textMuted hover:bg-jarvis-primary/10 hover:text-jarvis-primary'
            } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
            aria-label={isRecording ? 'Stop recording' : 'Start voice input'}
            aria-pressed={isRecording}
          >
            {isRecording ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
            {isRecording && (
              <span className="absolute -top-1 -right-1 w-2 h-2 bg-jarvis-recording rounded-full animate-ping" />
            )}
          </button>

          {/* Send Button */}
          <button
            type="submit"
            disabled={isEmpty || disabled}
            className={`btn-icon transition-all duration-200 group ${!isEmpty && !disabled
              ? 'bg-gradient-to-br from-jarvis-primary to-jarvis-primaryHover text-white shadow-lg shadow-jarvis-primary/30 hover:shadow-xl hover:shadow-jarvis-primary/40 hover:scale-105'
              : 'text-jarvis-textMuted opacity-50 cursor-not-allowed'
            }`}
            aria-label="Send message"
          >
            <ArrowUpRight className="w-5 h-5 group-hover:translate-x-1 group-hover:-translate-y-1 transition-transform" />
          </button>
        </div>
      </div>
    </form>
  )
}