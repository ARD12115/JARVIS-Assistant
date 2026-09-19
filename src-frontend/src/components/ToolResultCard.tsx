import { ToolCall, ToolResult } from '../types'
import { Terminal, CheckCircle, XCircle, Loader2, ChevronDown, ChevronUp } from 'lucide-react'
import { useState } from 'react'

interface ToolResultCardProps {
  toolCall: ToolCall
  result: ToolResult | null
  isPending?: boolean
}

export function ToolResultCard({ toolCall, result, isPending }: ToolResultCardProps) {
  const [expanded, setExpanded] = useState(false)
  const funcName = toolCall.function.name
  const funcArgs = toolCall.function.arguments

  let argsDisplay = ''
  try {
    const parsed = JSON.parse(funcArgs)
    argsDisplay = Object.entries(parsed)
      .map(([k, v]) => `${k}: ${typeof v === 'string' ? `"${v}"` : String(v)}`)
      .join(', ')
  } catch {
    argsDisplay = funcArgs
  }

  const getStatusIcon = () => {
    if (isPending || result === null) return <Loader2 className="w-4 h-4 animate-spin text-jarvis-accent" />
    if (result.success) return <CheckCircle className="w-4 h-4 text-jarvis-primary" />
    return <XCircle className="w-4 h-4 text-red-400" />
  }

  const getStatusText = () => {
    if (isPending || result === null) return 'Running...'
    if (result.success) return 'Completed'
    return `Error: ${result.error}`
  }

  return (
    <div className="bg-jarvis-toolMsg border border-jarvis-border/50 rounded-lg overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-3 px-3 py-2.5 hover:bg-jarvis-toolMsg/80 transition-colors text-left"
        aria-expanded={expanded}
      >
        <div className="flex items-center gap-2">
          <Terminal className="w-4 h-4 text-jarvis-accent" />
          <span className="font-mono text-sm text-jarvis-text">{funcName}</span>
        </div>
        <span className="flex-1 text-right text-xs text-jarvis-textMuted font-mono">{argsDisplay}</span>
        <div className="flex items-center gap-2">
          {getStatusIcon()}
          <span className="text-xs text-jarvis-textMuted">{getStatusText()}</span>
          {expanded ? <ChevronUp className="w-4 h-4 text-jarvis-textMuted" /> : <ChevronDown className="w-4 h-4 text-jarvis-textMuted" />}
        </div>
      </button>

      {expanded && result && (
        <div className="border-t border-jarvis-border/50 p-3 bg-jarvis-bg font-mono text-xs text-jarvis-textMuted max-h-64 overflow-auto">
          <pre>{JSON.stringify(result.data || { error: result.error }, null, 2)}</pre>
        </div>
      )}
    </div>
  )
}