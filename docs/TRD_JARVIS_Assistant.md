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
│  │  /chat      │  │  (NVIDIA    │  │  (Plugins)  │  │  (SQLite)   │        │
│  │  /voice     │  │   NIM +     │  │             │  │             │        │
│  │  /tools     │  │   OpenRouter)│  │             │  │             │        │
│  │  /memory    │  │             │  │             │  │             │        │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘        │
└─────────┼────────────────┼────────────────┼────────────────┼────────────────┘
          │                │                │                │
     ┌────┴────┬────┐ ┌────┴────┐    ┌─────┴─────┐    ┌─────┴─────┐
     ▼         ▼    ▼    ▼         ▼    ▼           ▼    ▼           ▼
  NVIDIA   OpenR  Time  Weather WebSearch FileOps  SystemInfo CodeExec
   NIM      API   Tool  Tool    Tool     Tool     Tool     Tool
```

---

### 2. Component Specifications

#### 2.1 Configuration System (`src_python/config.py`)

| Parameter | Type | Default | Source | Description |
|-----------|------|---------|--------|-------------|
| `primary_backend` | str | `"nvidia_nim"` | ENV | Primary LLM backend name |
| `nvidia_nim_api_key` | str | `""` | ENV | NVIDIA NIM API key |
| `nvidia_nim_model` | str | `"nvidia/nemotron-3-super-120b-a12b"` | ENV | NVIDIA NIM model |
| `nvidia_nim_base_url` | str | `"https://integrate.api.nvidia.com/v1"` | ENV | NVIDIA NIM API base URL |
| `openrouter_key` | str | `""` | ENV | OpenRouter API key |
| `openrouter_model` | str | `"meta-llama/llama-3.1-8b-instruct:free"` | ENV | Default OpenRouter model |
| `fallback_backends` | List[str] | `["openrouter"]` | Code | Fallback order |
| `db_path` | str | `"jarvis.db"` | ENV | SQLite database path |
| `log_level` | str | `"INFO"` | ENV | Logging level |
| `voice_enabled` | bool | `false` | ENV | Enable voice I/O |
| `api_host` | str | `"127.0.0.1"` | ENV | FastAPI bind address |
| `api_port` | int | `8765` | ENV | FastAPI port |

**Note:** Ollama, RunPod, Anthropic backends removed per user request. Only NVIDIA NIM + OpenRouter remain.

#### 2.2 LLM Backend Interface (`src_python/llm/base.py`)

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

#### 2.3 LLM Manager (`src_python/llm/manager.py`)

| Method | Description |
|--------|-------------|
| `get_healthy_backend()` | Returns first backend passing health check |
| `chat(messages, **kwargs)` | Tries backends in order until success |
| `chat_stream(messages, **kwargs)` | Streaming version with fallback |
| `invalidate_cache(backend_name)` | Forces re-check on next call |
| `get_status()` | Returns dict of all backends + health |

**Health Check Strategy:**
- NVIDIA NIM: `GET /models` endpoint (5s timeout)
- OpenRouter: Key presence + test request on first use
- Cache TTL: 30 seconds (known issue: causes intermittent false negatives)

**Fallback Logic:**
1. Try primary backend (NVIDIA NIM) if healthy
2. Iterate fallbacks in order (OpenRouter), skip unhealthy
3. If all unhealthy, try anyway (last resort)
4. On failure: invalidate cache, try next
5. After all exhausted: raise `AllBackendsFailedError`

**Known Issue:** Health check cache TTL (30s) causes intermittent "healthy: false" for NVIDIA even though direct API calls return 200. Direct API test always works.

#### 2.4 Tool Registry (`src_python/tools/registry.py`)

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

**Note:** 7 tools currently (code_exec is the 8th but flagged as security risk — no sandbox).

#### 2.5 Session Memory (`src_python/memory/session.py`)

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

**Known Issues:**
- `MAX_HISTORY_LIMIT` constant missing (referenced at line 189)
- `session_exists()` method missing (referenced at line 192)

#### 2.6 Agent Core (`src_python/agent/core.py`)

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

**NVIDIA NIM / OpenRouter (OpenAI-compatible):**
```json
// Request
POST /v1/chat/completions
{
  "model": "nvidia/nemotron-3-super-120b-a12b",
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
| Node | 20+ (npm recommended — pnpm has Windows binary issues) |
| Python | 3.11+ |
| GPU | RTX 3050 Ti 4GB (local inference not used — NIM runs in cloud) |
| RAM | 16GB+ recommended |
| Disk | 5GB free (models, DB, logs, node_modules) |

#### 5.2 NVIDIA NIM (Cloud)

| Spec | Recommendation |
|------|----------------|
| Model | `nvidia/nemotron-3-super-120b-a12b` (tested working) |
| Endpoint | `https://integrate.api.nvidia.com/v1` |
| Auth | Bearer token (`nvapi-xxx`) |
| Cost | Free tier available; pay-per-use beyond |

**Available Models:** Check `https://integrate.api.nvidia.com/v1/models`

#### 5.3 OpenRouter (Fallback)

| Spec | Recommendation |
|------|----------------|
| Model | `meta-llama/llama-3.1-8b-instruct:free` (default free tier) |
| Endpoint | `https://openrouter.ai/api/v1` |
| Auth | Bearer token (`sk-or-xxx`) |

---

### 6. Security Requirements

| Requirement | Implementation |
|-------------|----------------|
| API keys never in code | `.env` + `.gitignore`; `python-dotenv` with explicit project root path |
| No secrets in logs | Structured logging filters `Authorization` headers |
| Tool sandbox | `code_exec` runs in subprocess with timeout, no network — **NOT YET IMPLEMENTED** |
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
cd src_python
PYTHONPATH="C:/Projects/JARVIS-Assistant/src_python" .venv/Scripts/python.exe main.py

# Terminal 2: Frontend dev server
cd src-frontend
npm run dev

# Terminal 3: Tauri dev
cd src-tauri
npm run tauri dev
```

#### 8.2 Production Build

```bash
cd src-tauri
npm run tauri build
# Output: src-tauri/target/release/bundle/
```

#### 8.3 NVIDIA NIM Setup

1. Create account at [NVIDIA NGC](https://ngc.nvidia.com)
2. Get API key from [NVIDIA NIM](https://build.nvidia.com)
3. Add to `.env`:
   ```env
   NVIDIA_NIM_API_KEY=nvapi-xxx
   NVIDIA_NIM_MODEL=nvidia/nemotron-3-super-120b-a12b
   ```

#### 8.4 Google Cloud Run Deployment

The Python API can be deployed as a private Cloud Run service. The Tauri desktop application continues to use its locally managed Python sidecar.

```bash
gcloud config set project YOUR_PROJECT_ID
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com
gcloud run deploy jarvis-api \
  --source . \
  --region us-central1 \
  --no-allow-unauthenticated
```

---

### 9. Known Issues & TODOs

| Issue | Location | Priority |
|-------|----------|----------|
| Health check cache TTL causes false negatives | `llm/manager.py` | High |
| OpenRouter placeholder key returns 401 | `.env` | Medium |
| `code_exec` tool has no sandbox | `tools/builtin/code_exec_tool.py` | High |
| `MAX_HISTORY_LIMIT` constant missing | `memory/session.py` | Medium |
| `session_exists()` method missing | `memory/session.py` | Medium |
| Frontend hooks (`useChat`, `useVoice`) not implemented | `src-frontend/src/hooks/` | Medium |
| Streaming UI not connected to chatStore | `src-frontend/src/components/MessageBubble.tsx` | Medium |
| TTS `synthesize()` signature mismatch (voice param ignored) | `voice/tts.py` | Low |

---

### 10. Current Verified State (Sept 19, 2026)

| Endpoint | Status | Tested |
|----------|--------|--------|
| `GET /health` | ✅ Working | Both backends show healthy (cache-dependent) |
| `POST /chat` | ✅ Working | Returns NVIDIA NIM response |
| `POST /chat/stream` | ✅ Working | SSE streaming token-by-token |
| `GET /memory/sessions` | ✅ Working | Returns session list |
| `GET /memory/history/{id}` | ✅ Working | Returns conversation history |
| Frontend `GET /` | ✅ Working | Serves React app on port 5173 |
| Tauri compile | ✅ Working | `cargo build` succeeds |
| Direct NVIDIA API | ✅ Working | `nvidia/nemotron-3-super-120b-a12b` returns 200 |