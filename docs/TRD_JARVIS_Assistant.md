# Technical Requirements Document (TRD)
## JARVIS Assistant — Technical Specification (Tauri Desktop App)

---

### 1. System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         JARVIS Desktop App (Tauri 2.x)                       │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                        React Frontend (WebView)                      │    │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │    │
│  │  │ ChatWindow  │ │ MessageList │ │ InputBar    │ │ VoiceButton │   │    │
│  │  │ Sidebar     │ │ ToolCards   │ │ Waveform    │ │ Settings    │   │    │
│  │  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘   │    │
│  └─────────┼────────────────┼────────────────┼────────────────┼────────┘    │
│            │                │                │                │             │
│            ▼                ▼                ▼                ▼             │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                      Zustand Store + IPC Layer                       │    │
│  │  useChat.ts ◄──► invoke('send_message') ◄──► Tauri Commands (Rust)  │    │
│  │  useVoice.ts ◄──► invoke('voice_stt/tts') ◄──► Tauri Commands       │    │
│  └────────────────────────────────┬────────────────────────────────────┘    │
└───────────────────────────────────┼─────────────────────────────────────────┘
                                    │ Tauri IPC / HTTP (localhost:8765)
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      Python Backend (FastAPI Sidecar)                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │  FastAPI    │  │  LLM        │  │  Tool       │  │  Memory     │        │
│  │  Routes     │  │  Manager    │  │  Registry   │  │  Manager    │        │
│  │  /chat      │  │  (Multi-    │  │  (Plugins)  │  │  (SQLite)   │        │
│  │  /voice     │  │   Backend)  │  │             │  │             │        │
│  │  /tools     │  │             │  │             │  │             │        │
│  │  /memory    │  │             │  │             │  │             │        │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘        │
└─────────┼────────────────┼────────────────┼────────────────┼────────────────┘
          │                │                │                │
     ┌────┴────┬────┐ ┌────┴────┐    ┌─────┴─────┐    ┌─────┴─────┐
     ▼         ▼    ▼    ▼         ▼    ▼           ▼    ▼           ▼
  RunPod   Ollama OpenR  Time  Weather WebSearch FileOps  SystemInfo CodeExec
  vLLM     Local  API   Tool  Tool    Tool     Tool     Tool     Tool
```

---

### 2. Component Specifications

#### 2.1 Configuration System (`src-python/config.py`)

| Parameter | Type | Default | Source | Description |
|-----------|------|---------|--------|-------------|
| `primary_backend` | str | "runpod" | ENV | Primary LLM backend name |
| `runpod_endpoint` | str | "" | ENV | RunPod vLLM endpoint URL |
| `runpod_token` | str | "" | ENV | RunPod API token |
| `ollama_host` | str | "http://localhost:11434" | ENV | Ollama API base URL |
| `ollama_model` | str | "llama3.1:8b" | ENV | Default Ollama model |
| `openrouter_key` | str | "" | ENV | OpenRouter API key |
| `anthropic_key` | str | "" | ENV | Anthropic API key |
| `fallback_backends` | List[str] | ["ollama", "openrouter"] | Code | Fallback order |
| `db_path` | str | "jarvis.db" | ENV | SQLite database path |
| `log_level` | str | "INFO" | ENV | Logging level |
| `voice_enabled` | bool | false | ENV | Enable voice I/O |
| `api_host` | str | "127.0.0.1" | ENV | FastAPI bind address |
| `api_port` | int | 8765 | ENV | FastAPI port |

#### 2.2 LLM Backend Interface (`src-python/llm/base.py`)

```python
@dataclass
class Message:
    role: str          # "system" | "user" | "assistant" | "tool"
    content: str
    tool_calls: List[ToolCall] = None
    tool_call_id: str = None

@dataclass
class ChatResponse:
    content: str
    model: str
    usage: Dict[str, int] = None
    latency_ms: int = None

@dataclass
class ChatStreamChunk:
    content: str
    done: bool
    tool_calls: List[ToolCall] = None

class LLMBackend(ABC):
    @abstractmethod
    def chat(self, messages: List[Message], **kwargs) -> ChatResponse: ...
    
    @abstractmethod
    async def chat_stream(self, messages: List[Message], **kwargs) -> AsyncGenerator[ChatStreamChunk, None]: ...
    
    @abstractmethod
    def is_available(self) -> bool: ...
    
    @abstractmethod
    def get_models(self) -> List[str]: ...
```

#### 2.3 LLM Manager (`src-python/llm/manager.py`)

| Method | Description |
|--------|-------------|
| `get_healthy_backend()` | Returns first backend passing health check |
| `chat(messages, **kwargs)` | Tries backends in order until success |
| `chat_stream(messages, **kwargs)` | Streaming version with fallback |
| `invalidate_cache(backend_name)` | Forces re-check on next call |
| `get_status()` | Returns dict of all backends + health |

**Health Check Strategy:**
- RunPod: `GET /health` endpoint (5s timeout)
- Ollama: `GET /api/tags` (5s timeout)
- OpenRouter: Key presence + test request on first use
- Cache TTL: 30 seconds

**Fallback Logic:**
1. Try primary backend if healthy
2. Iterate fallbacks in order, skip unhealthy
3. If all unhealthy, try anyway (last resort)
4. On failure: invalidate cache, try next
5. After all exhausted: raise `AllBackendsFailedError`

#### 2.4 Tool Registry (`src-python/tools/registry.py`)

```python
@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: Dict  # JSON Schema
    returns: Dict     # JSON Schema

class ToolRegistry:
    def register(self, tool: Tool) -> None: ...
    def get(self, name: str) -> Tool: ...
    def list_tools(self) -> List[ToolSpec]: ...
    def execute(self, name: str, **kwargs) -> ToolResult: ...
    def to_openai_functions(self) -> List[Dict]: ...
```

**Built-in Tools (MVP):**

| Tool | Description | Parameters | External Dependency |
|------|-------------|------------|---------------------|
| `get_time` | Current time in timezone | `timezone?: str` | None |
| `get_weather` | Current weather for location | `location: str` | OpenWeatherMap API |
| `web_search` | Search web, return snippets | `query: str, max_results?: int` | Brave/SerpAPI or browser-use |
| `system_info` | CPU, RAM, GPU, disk usage | None | `psutil`, `GPUtil` |
| `file_read` | Read file with line range | `path: str, offset?: int, limit?: int` | None |
| `file_write` | Write file (create dirs) | `path: str, content: str` | None |
| `file_list` | List directory tree | `path: str, depth?: int` | None |
| `code_exec` | Run Python in sandbox | `code: str, timeout?: int` | `subprocess` (isolated) |

#### 2.5 Session Memory (`src-python/memory/session.py`)

**Schema:**
```sql
CREATE TABLE conversations (
    id INTEGER PRIMARY KEY,
    session_id TEXT NOT NULL,
    turn_index INTEGER NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    tool_calls TEXT,           -- JSON
    tool_results TEXT,         -- JSON
    latency_ms INTEGER,
    backend_used TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_session_turn ON conversations(session_id, turn_index);
CREATE INDEX idx_session_created ON conversations(created_at);
```

**API:**
```python
class SessionMemory:
    def __init__(self, db_path: str, session_id: str = None): ...
    
    def add_turn(self, role: str, content: str, **metadata) -> int: ...
    def get_history(self, limit: int = 50) -> List[Message]: ...
    def search(self, query: str, limit: int = 10) -> List[Message]: ...
    def summarize(self, max_turns: int = 100) -> str: ...
    def get_session_id(self) -> str: ...
    def new_session(self) -> str: ...
    def list_sessions(self) -> List[SessionSummary]: ...
```

#### 2.6 Agent Core (`src-python/agent/core.py`)

```python
class Agent:
    def __init__(
        self,
        llm_manager: LLMManager,
        tool_registry: ToolRegistry,
        memory: SessionMemory,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT
    ): ...
    
    async def chat_stream(self, user_input: str, session_id: str) -> AsyncGenerator[ChatStreamChunk, None]: ...
    async def execute_tool_calls(self, tool_calls: List[ToolCall]) -> List[ToolResult]: ...
    def build_prompt(self, user_input: str, session_id: str) -> List[Message]: ...
```

**System Prompt Structure:**
```
You are JARVIS, an AI assistant with access to tools.
Current date: {date}
User: {user_context}

Available tools: {tool_descriptions}

Guidelines:
- Use tools when you need real-time data or to take action
- Think step-by-step for complex requests
- Be concise but thorough
- Admit uncertainty; don't hallucinate
```

---

### 3. Data Flow

#### 3.1 Chat Turn (Text + Streaming)

```
User Input (React InputBar)
    │
    ▼
useChat.ts → invoke('send_message', {session_id, content})
    │
    ▼
Tauri Command (Rust) → HTTP POST http://127.0.0.1:8765/chat/stream
    │
    ▼
FastAPI /chat/stream → Agent.build_prompt() → LLMManager.chat_stream()
    │
    ▼
SSE Stream: ChatStreamChunk tokens
    │
    ▼
Tauri Event Stream → React useChat.ts → Zustand store → MessageBubble (streaming)
    │
    ▼
Tool Calls (if any) → ToolRegistry.execute() → ToolResult
    │
    ▼
Inject results → LLM again (if needed) → More chunks
    │
    ▼
Final chunk (done=true) → Memory.add_turn() for all turns
```

#### 3.2 Voice Turn

```
Push-to-Talk (VoiceButton hold)
    │
    ▼
MediaRecorder → audio/webm chunks
    │
    ▼
invoke('voice_stt', {audio_base64}) → Tauri → FastAPI /voice/stt
    │
    ▼
faster-whisper → text
    │
    ▼
[Same as Chat Turn from text input]
    │
    ▼
Final response text
    │
    ▼
invoke('voice_tts', {text}) → FastAPI /voice/tts → edge-tts → MP3 bytes
    │
    ▼
base64 audio → React AudioContext → playback + waveform visualizer
```

---

### 4. API Contracts

#### 4.1 FastAPI Routes

**POST /chat/stream**
```json
// Request
{
  "session_id": "uuid",
  "content": "Hello JARVIS",
  "stream": true
}

// Response (SSE)
data: {"content": "H", "done": false}
data: {"content": "He", "done": false}
...
data: {"content": "Hello! How can I help?", "done": true, "tool_calls": []}
```

**POST /voice/stt**
```json
// Request (multipart/form-data)
audio: <webm/opus blob>

// Response
{"text": "Hello JARVIS"}
```

**POST /voice/tts**
```json
// Request
{"text": "Hello there!", "voice": "en-US-AriaNeural"}

// Response
Content-Type: audio/mpeg
<body: mp3 bytes>
```

**GET /memory/sessions**
```json
// Response
[{"session_id": "uuid", "started_at": "...", "turn_count": 5, "preview": "Hello..."}]
```

**GET /memory/history/{session_id}**
```json
// Response
[{"role": "user", "content": "...", "tool_calls": [], ...}]
```

#### 4.2 LLM Backend Request/Response

**RunPod / OpenRouter (OpenAI-compatible):**
```json
// Request
POST /v1/chat/completions
{
  "model": "meta-llama/Meta-Llama-3.1-8B-Instruct",
  "messages": [{"role": "user", "content": "Hello"}],
  "temperature": 0.7,
  "max_tokens": 2048,
  "stream": true
}

// Response (SSE)
data: {"choices": [{"delta": {"content": "H"}}]}
data: {"choices": [{"delta": {"content": "He"}}]}
...
data: {"choices": [{"delta": {}, "finish_reason": "stop"}]}
```

**Ollama:**
```json
// Request
POST /api/chat
{
  "model": "llama3.1:8b",
  "messages": [{"role": "user", "content": "Hello"}],
  "stream": true
}

// Response (NDJSON)
{"message": {"content": "H"}, "done": false}
{"message": {"content": "He"}, "done": false}
...
{"message": {"content": ""}, "done": true}
```

#### 4.3 Tool Calling (OpenAI Function Calling Format)

```json
// LLM requests tool call
{
  "tool_calls": [{
    "id": "call_abc123",
    "type": "function",
    "function": {
      "name": "get_weather",
      "arguments": "{\"location\": \"Bangalore\"}"
    }
  }]
}

// Tool result injected back
{
  "role": "tool",
  "tool_call_id": "call_abc123",
  "content": "{\"temperature\": 28, \"condition\": \"Sunny\"}"
}
```

---

### 5. Infrastructure Requirements

#### 5.1 Local Development

| Component | Spec |
|-----------|------|
| OS | Windows 11 (WebView2), Linux (WebKitGTK), macOS (WebKit) |
| Rust | 1.75+ (for Tauri 2.x) |
| Node | 20+ (pnpm recommended) |
| Python | 3.11+ |
| GPU | RTX 3050 Ti 4GB (local inference) |
| RAM | 16GB+ recommended |
| Disk | 5GB free (models, DB, logs, node_modules) |

#### 5.2 Remote GPU (RunPod)

| Spec | Recommendation |
|------|----------------|
| GPU | RTX 3090 / 4090 / A100 (24GB+) for 8B+ models |
| vLLM | `--model meta-llama/Meta-Llama-3.1-8B-Instruct --dtype half --gpu-memory-utilization 0.9` |
| Endpoint | Serverless with `min_workers=1` for warm standby |
| Cost | ~$0.30/hr (A10) → ~$7/day if 24/7; serverless per-second cheaper |

#### 5.3 Local Ollama Models (4GB VRAM)

| Model | Size (4-bit) | VRAM | Quality |
|-------|--------------|------|---------|
| `llama3.2:3b` | ~2GB | ~2.5GB | Basic |
| `qwen2.5:7b` | ~4GB | ~4.5GB* | Good |
| `phi3.5:3.8b` | ~2.3GB | ~2.8GB | Strong reasoning |
| `gemma2:2b` | ~1.6GB | ~2GB | Lightweight |

*May need `--gpu-layers 20` offload to system RAM

---

### 6. Security Requirements

| Requirement | Implementation |
|-------------|----------------|
| API keys never in code | `.env` + `.gitignore`; `python-dotenv` |
| No secrets in logs | Structured logging filters `Authorization` headers |
| Tool sandbox | `code_exec` runs in subprocess with timeout, no network |
| Input validation | All tool params validated against JSON Schema |
| Dependency scanning | `pip-audit` / `cargo audit` in CI; pinned versions |
| Tauri allowlist | Minimal `tauri.conf.json` permissions (fs, shell, http scoped) |

---

### 7. Testing Strategy

| Layer | Tool | Coverage Target |
|-------|------|-----------------|
| Unit (Python) | pytest | >80% core modules |
| Unit (Rust) | cargo test | Commands, sidecar management |
| Unit (Frontend) | Vitest + React Testing Library | Components, hooks |
| Integration | pytest + testcontainers | LLM backends, tools, memory |
| E2E | Playwright (Tauri) | Full chat flows, fallback, voice |

**Test Fixtures:**
- Mock LLM backends with recorded responses
- Temporary SQLite DB per test
- Fake tool implementations
- Tauri mock for frontend tests

---

### 8. Deployment & Operations

#### 8.1 Local Development
```bash
# Terminal 1: Python backend
cd src-python
uv pip install -e .
uv run python main.py

# Terminal 2: Frontend dev server
cd src-frontend
pnpm dev

# Terminal 3: Tauri dev
cd src-tauri
pnpm tauri dev
```

#### 8.2 Production Build
```bash
cd src-tauri
pnpm tauri build
# Output: src-tauri/src-tauri/target/release/bundle/
```

#### 8.3 RunPod Deployment
```bash
# On RunPod instance
docker run -d \
  --gpus all \
  -p 8000:8000 \
  -e HF_TOKEN=$HF_TOKEN \
  vllm/vllm-openai:latest \
  --model meta-llama/Meta-Llama-3.1-8B-Instruct \
  --dtype half
```

#### 8.4 Daily Progress Automation
```bash
# Cron (runs at 23:59 daily)
0 23 * * * cd /Projects/JARVIS-Assistant && python scripts/daily_progress.py
```

---

### 9. Monitoring & Observability

| Metric | Collection | Alert Threshold |
|--------|------------|-----------------|
| Request latency (p50/p95) | Structured logs | p95 > 10s |
| Backend health | Health check cache | Any backend down >5min |
| Tool error rate | Counter per tool | >5% in 1hr |
| Memory DB size | File stat | >100MB |
| Token usage | LLM response usage | N/A (tracking only) |
| Tauri IPC latency | Rust tracing | >500ms |

**Log Format (JSON):**
```json
{
  "timestamp": "2026-09-12T19:45:00Z",
  "level": "INFO",
  "component": "llm_manager",
  "event": "chat_completion",
  "backend": "runpod",
  "latency_ms": 1234,
  "tokens_in": 150,
  "tokens_out": 89,
  "fallback": false
}
```

---

### 10. Extensibility Points

| Extension Point | How to Add |
|-----------------|------------|
| New LLM Backend | Implement `LLMBackend`, add to `BACKEND_MAP` in factory |
| New Tool | Subclass `Tool`, register in `ToolRegistry` at startup |
| New Memory Backend | Implement `SessionMemory` interface, swap in `Agent` |
| New Voice Engine | Implement `STTEngine`/`TTSEngine` interfaces |
| New Frontend Component | Add React component, register in `ChatWindow` |
| New Tauri Command | Add `#[tauri::command]` function, register in `main.rs` |

---

### 11. File Structure (Target)

```
JARVIS-Assistant/
├── .env.example
├── .gitignore
├── README.md
├── docs/
│   ├── PRD_JARVIS_Assistant.md
│   ├── TRD_JARVIS_Assistant.md
│   ├── SKILLS_JARVIS_Assistant.md
│   └── progress/
│       └── YYYY-MM-DD.md
├── scripts/
│   ├── daily_progress.py
│   └── deploy_runpod.sh
├── src-python/
│   ├── pyproject.toml
│   ├── main.py                 # FastAPI entry
│   ├── config.py
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── manager.py
│   │   ├── factory.py
│   │   ├── runpod_client.py
│   │   ├── ollama_client.py
│   │   └── openrouter_client.py
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── registry.py
│   │   └── builtin/
│   │       ├── __init__.py
│   │       ├── time_tool.py
│   │       ├── weather_tool.py
│   │       ├── web_search_tool.py
│   │       ├── system_info_tool.py
│   │       ├── file_tools.py
│   │       └── code_exec_tool.py
│   ├── memory/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   └── session.py
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── core.py
│   │   └── prompts.py
│   └── voice/
│       ├── __init__.py
│       ├── stt.py
│       ├── tts.py
│       └── manager.py
├── src-frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   ├── index.html
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── index.css
│   │   ├── components/
│   │   │   ├── ChatWindow.tsx
│   │   │   ├── MessageBubble.tsx
│   │   │   ├── InputBar.tsx
│   │   │   ├── VoiceButton.tsx
│   │   │   ├── ToolResultCard.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   └── WaveformVisualizer.tsx
│   │   ├── hooks/
│   │   │   ├── useChat.ts
│   │   │   └── useVoice.ts
│   │   ├── store/
│   │   │   └── chatStore.ts
│   │   ├── api/
│   │   │   └── tauri.ts
│   │   └── types/
│   │       └── index.ts
│   └── public/
├── src-tauri/
│   ├── Cargo.toml
│   ├── tauri.conf.json
│   ├── src/
│   │   ├── main.rs
│   │   ├── python_sidecar.rs
│   │   └── commands/
│   │       ├── mod.rs
│   │       ├── chat.rs
│   │       ├── voice.rs
│   │       ├── tools.rs
│   │       └── memory.rs
│   └── icons/
└── tests/
    ├── python/
    │   ├── test_config.py
    │   ├── test_llm_backends.py
    │   ├── test_llm_manager.py
    │   ├── test_tools.py
    │   ├── test_memory.py
    │   └── test_agent.py
    ├── rust/
    └── frontend/
```

---

### 12. Open Technical Decisions

| Decision | Options | Recommendation |
|----------|---------|----------------|
| Web search provider | Brave API / SerpAPI / browser-use / duckduckgo-html | Start with browser-use (no API key) |
| Voice STT | faster-whisper / whisper.cpp / Vosk | faster-whisper (Python, good accuracy) |
| Voice TTS | edge-tts / piper / coqui / bark | edge-tts (free, many voices, no model download) |
| Wake word | Porcupine / Picovoice / custom / none | Skip for MVP; push-to-talk only |
| Code execution sandbox | subprocess / docker / firejail / wasm | subprocess with timeout + restricted env |
| Config format | TOML / YAML / JSON / .env only | .env + dataclass (current) |
| Logging | structlog / loguru / stdlib logging | structlog (structured, fast) |
| State management | Zustand / Redux Toolkit / Jotai | Zustand (simple, TypeScript-first) |
| Markdown rendering | react-markdown / remark / MDX | react-markdown + rehype-highlight |

---

### 13. References

- [Tauri 2.x Docs](https://tauri.app/v2/)
- [vLLM OpenAI Compatible API](https://docs.vllm.ai/en/latest/serving/openai_compatible_server.html)
- [Ollama API](https://github.com/ollama/ollama/blob/main/docs/api.md)
- [OpenRouter API](https://openrouter.ai/docs)
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
- [edge-tts](https://github.com/rany2/edge-tts)
- [Hermes Kanban Operations](skills/autonomous-ai-agents/hermes-kanban-operations)
- [Plan Skill](skills/software-development/plan)