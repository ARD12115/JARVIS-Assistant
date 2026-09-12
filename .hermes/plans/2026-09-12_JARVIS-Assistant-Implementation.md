# JARVIS Assistant Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Build a JARVIS-like AI assistant with multi-backend LLM support (remote GPU + local fallback), voice capabilities, tool registry, and persistent memory — delivered as a **Tauri desktop app** (Rust + React/TypeScript frontend, Python backend) with chat UI, daily progress tracking, and kanban integration.

**Architecture:** Tauri desktop app with:
- **Frontend:** React + TypeScript + Tailwind CSS (chat UI, streaming messages, voice controls)
- **Backend:** Python (FastAPI) for LLM orchestration, tools, memory — communicates via Tauri IPC
- **LLM Layer:** Multi-backend (RunPod vLLM primary → Ollama local → OpenRouter/Anthropic fallback) with auto-failover
- **Voice:** faster-whisper STT + edge-tts TTS (push-to-talk, optional wake word)
- **Memory:** SQLite session persistence
- **Kanban:** Hermes kanban for task tracking, daily progress auto-generation

**Tech Stack:** 
- Frontend: React 18, TypeScript, Tailwind CSS, Vite, Zustand (state), React Markdown
- Backend: Python 3.11+, FastAPI, httpx, SQLite, faster-whisper, edge-tts, Ollama SDK, vLLM client, python-dotenv
- Desktop: Tauri 2.x (Rust), Webview2 (Windows)
- Dev: pnpm, uv/pip, cargo

---

## Phase 1: Project Foundation & Multi-Backend LLM Layer (Days 1-3)

### Task 1: Initialize Project Structure & Config

**Objective:** Set up Tauri + React + Python repo skeleton, config management, and environment handling.

**Files:**
- Create: `src-python/config.py`
- Create: `src-python/__init__.py`
- Create: `src-python/pyproject.toml`
- Create: `.env.example`
- Create: `src-tauri/` (Tauri app scaffold via `cargo tauri init`)
- Create: `src-frontend/` (React + TS + Vite + Tailwind via `pnpm create vite`)
- Create: `src-frontend/src/store/chatStore.ts` (Zustand)
- Create: `.gitignore`

**Step 1: Write failing test**
```python
# tests/test_config.py
def test_config_loads_env():
    from src_python.config import Config
    cfg = Config()
    assert hasattr(cfg, 'primary_backend')
    assert hasattr(cfg, 'fallback_backends')
```

**Step 2: Run test to verify failure**
```bash
pytest tests/test_config.py::test_config_loads_env -v
# Expected: FAIL — module not found
```

**Step 3: Write minimal implementation**
```python
# src-python/config.py
import os
from dataclasses import dataclass, field
from typing import List
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    primary_backend: str = os.getenv("PRIMARY_BACKEND", "runpod")
    runpod_endpoint: str = os.getenv("RUNPOD_ENDPOINT", "")
    runpod_token: str = os.getenv("RUNPOD_TOKEN", "")
    ollama_host: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
    openrouter_key: str = os.getenv("OPENROUTER_API_KEY", "")
    anthropic_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    fallback_backends: List[str] = field(default_factory=lambda: ["ollama", "openrouter"])
    db_path: str = os.getenv("JARVIS_DB", "jarvis.db")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    voice_enabled: bool = os.getenv("VOICE_ENABLED", "false").lower() == "true"
    api_host: str = os.getenv("API_HOST", "127.0.0.1")
    api_port: int = int(os.getenv("API_PORT", "8765"))
```

**Step 4: Run test to verify pass**
```bash
pytest tests/test_config.py::test_config_loads_env -v
# Expected: PASS
```

**Step 5: Commit**
```bash
git add src-python/config.py tests/test_config.py src-python/pyproject.toml .env.example .gitignore
git commit -m "feat: project foundation with multi-backend config"
```

---

### Task 2: LLM Backend Abstraction & Clients

**Objective:** Create unified interface for all LLM backends with automatic fallback.

**Files:**
- Create: `src/llm/base.py`
- Create: `src/llm/runpod_client.py`
- Create: `src/llm/ollama_client.py`
- Create: `src/llm/openrouter_client.py`
- Create: `src/llm/factory.py`
- Create: `tests/test_llm_backends.py`

**Step 1: Write failing test**
```python
# tests/test_llm_backends.py
def test_factory_creates_backend():
    from src.llm.factory import create_backend
    from src.config import Config
    cfg = Config()
    backend = create_backend(cfg.primary_backend, cfg)
    assert hasattr(backend, 'chat')
    assert callable(backend.chat)
```

**Step 2: Run test to verify failure**

**Step 3: Write implementations**
```python
# src/llm/base.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class Message:
    role: str
    content: str

@dataclass
class ChatResponse:
    content: str
    model: str
    usage: Optional[Dict[str, int]] = None

class LLMBackend(ABC):
    @abstractmethod
    def chat(self, messages: List[Message], **kwargs) -> ChatResponse:
        pass

    @abstractmethod
    def is_available(self) -> bool:
        pass
```

```python
# src/llm/runpod_client.py
import httpx
from typing import List
from src.llm.base import LLMBackend, Message, ChatResponse
from src.config import Config

class RunPodClient(LLMBackend):
    def __init__(self, config: Config):
        self.endpoint = config.runpod_endpoint
        self.token = config.runpod_token
        self.client = httpx.Client(timeout=60.0)
    
    def is_available(self) -> bool:
        if not self.endpoint or not self.token:
            return False
        try:
            resp = self.client.get(f"{self.endpoint}/health", timeout=5.0)
            return resp.status_code == 200
        except:
            return False
    
    def chat(self, messages: List[Message], **kwargs) -> ChatResponse:
        payload = {
            "model": kwargs.get("model", "meta-llama/Meta-Llama-3.1-8B-Instruct"),
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 2048),
        }
        headers = {"Authorization": f"Bearer {self.token}"}
        resp = self.client.post(f"{self.endpoint}/v1/chat/completions", json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        return ChatResponse(
            content=data["choices"][0]["message"]["content"],
            model=data.get("model", "unknown"),
            usage=data.get("usage")
        )
```

```python
# src/llm/ollama_client.py
import httpx
from typing import List
from src.llm.base import LLMBackend, Message, ChatResponse
from src.config import Config

class OllamaClient(LLMBackend):
    def __init__(self, config: Config):
        self.host = config.ollama_host
        self.model = config.ollama_model
        self.client = httpx.Client(timeout=120.0)
    
    def is_available(self) -> bool:
        try:
            resp = self.client.get(f"{self.host}/api/tags", timeout=5.0)
            return resp.status_code == 200
        except:
            return False
    
    def chat(self, messages: List[Message], **kwargs) -> ChatResponse:
        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
            "options": {
                "temperature": kwargs.get("temperature", 0.7),
                "num_predict": kwargs.get("max_tokens", 2048),
            }
        }
        resp = self.client.post(f"{self.host}/api/chat", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return ChatResponse(
            content=data["message"]["content"],
            model=data.get("model", self.model),
            usage={"prompt_tokens": data.get("prompt_eval_count", 0), "completion_tokens": data.get("eval_count", 0)}
        )
```

```python
# src/llm/openrouter_client.py
import httpx
from typing import List
from src.llm.base import LLMBackend, Message, ChatResponse
from src.config import Config

class OpenRouterClient(LLMBackend):
    def __init__(self, config: Config):
        self.key = config.openrouter_key
        self.client = httpx.Client(
            base_url="https://openrouter.ai/api/v1",
            timeout=60.0,
            headers={"Authorization": f"Bearer {self.key}"} if self.key else {}
        )
    
    def is_available(self) -> bool:
        return bool(self.key)
    
    def chat(self, messages: List[Message], **kwargs) -> ChatResponse:
        payload = {
            "model": kwargs.get("model", "meta-llama/llama-3.1-8b-instruct:free"),
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 2048),
        }
        resp = self.client.post("/chat/completions", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return ChatResponse(
            content=data["choices"][0]["message"]["content"],
            model=data.get("model", "unknown"),
            usage=data.get("usage")
        )
```

```python
# src/llm/factory.py
from src.llm.base import LLMBackend
from src.llm.runpod_client import RunPodClient
from src.llm.ollama_client import OllamaClient
from src.llm.openrouter_client import OpenRouterClient
from src.config import Config

BACKEND_MAP = {
    "runpod": RunPodClient,
    "ollama": OllamaClient,
    "openrouter": OpenRouterClient,
}

def create_backend(name: str, config: Config) -> LLMBackend:
    cls = BACKEND_MAP.get(name.lower())
    if not cls:
        raise ValueError(f"Unknown backend: {name}")
    return cls(config)

def create_all_backends(config: Config) -> list[LLMBackend]:
    backends = []
    # Primary first
    try:
        primary = create_backend(config.primary_backend, config)
        backends.append(primary)
    except Exception as e:
        print(f"Primary backend {config.primary_backend} failed to init: {e}")
    # Fallbacks
    for name in config.fallback_backends:
        if name != config.primary_backend:
            try:
                backends.append(create_backend(name, config))
            except Exception as e:
                print(f"Fallback {name} failed: {e}")
    return backends
```

**Step 4: Run test to verify pass**

**Step 5: Commit**

---

### Task 3: Auto-Fallback LLM Manager

**Objective:** Orchestrate backends with health checks and seamless fallback.

**Files:**
- Create: `src/llm/manager.py`
- Create: `tests/test_llm_manager.py`

**Step 1: Write failing test**

**Step 2: Write implementation**
```python
# src/llm/manager.py
import time
from typing import List
from src.llm.base import LLMBackend, Message, ChatResponse
from src.llm.factory import create_all_backends
from src.config import Config

class LLMManager:
    def __init__(self, config: Config):
        self.config = config
        self.backends = create_all_backends(config)
        self._health_cache = {}
        self._cache_ttl = 30  # seconds
    
    def _is_healthy(self, backend: LLMBackend) -> bool:
        now = time.time()
        if backend.__class__.__name__ in self._health_cache:
            cached, timestamp = self._health_cache[backend.__class__.__name__]
            if now - timestamp < self._cache_ttl:
                return cached
        healthy = backend.is_available()
        self._health_cache[backend.__class__.__name__] = (healthy, now)
        return healthy
    
    def get_healthy_backend(self) -> LLMBackend:
        for backend in self.backends:
            if self._is_healthy(backend):
                return backend
        # Last resort: return first anyway
        if self.backends:
            return self.backends[0]
        raise RuntimeError("No LLM backends configured")
    
    def chat(self, messages: List[Message], **kwargs) -> ChatResponse:
        last_error = None
        for backend in self.backends:
            if not self._is_healthy(backend):
                continue
            try:
                return backend.chat(messages, **kwargs)
            except Exception as e:
                last_error = e
                print(f"Backend {backend.__class__.__name__} failed: {e}")
                # Invalidate health cache for this backend
                self._health_cache[backend.__class__.__name__] = (False, time.time())
        raise RuntimeError(f"All backends failed. Last error: {last_error}")
```

**Step 3-5: Test, verify, commit**

---

## Phase 2: Tool Registry & Core Agent Loop (Days 4-6)

### Task 4: Tool Registry System

**Objective:** Pluggable tool system with schema validation and execution sandbox.

**Files:**
- Create: `src/tools/base.py`
- Create: `src/tools/registry.py`
- Create: `src/tools/builtin/` (time, weather, web_search, system_info, file_ops)
- Create: `tests/test_tools.py`

**Step 1-5: Implement with TDD**

```python
# src/tools/base.py
from abc import ABC, abstractmethod
from typing import Any, Dict
from dataclasses import dataclass

@dataclass
class ToolResult:
    success: bool
    data: Any = None
    error: str = None

class Tool(ABC):
    name: str
    description: str
    parameters: Dict  # JSON Schema
    
    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        pass
```

---

### Task 5: Session Memory (SQLite)

**Objective:** Persistent conversation history with search and summarization.

**Files:**
- Create: `src/memory/session.py`
- Create: `src/memory/models.py`
- Create: `tests/test_memory.py`

---

### Task 6: Core Agent Loop

**Objective:** Main REPL that coordinates LLM, tools, and memory.

**Files:**
- Create: `src/agent/core.py`
- Create: `src/agent/prompts.py`
- Create: `tests/test_agent.py`

---

## Phase 3: Tauri Frontend & Integration (Days 7-10)

### Task 7: React Chat UI (Frontend)

**Objective:** Build the chat interface with streaming messages, voice controls, and tool result rendering.

**Files:**
- Create: `src-frontend/src/components/ChatWindow.tsx`
- Create: `src-frontend/src/components/MessageBubble.tsx`
- Create: `src-frontend/src/components/InputBar.tsx`
- Create: `src-frontend/src/components/VoiceButton.tsx`
- Create: `src-frontend/src/components/ToolResultCard.tsx`
- Create: `src-frontend/src/components/Sidebar.tsx` (history, settings)
- Create: `src-frontend/src/hooks/useChat.ts` (WebSocket/IPC connection)
- Create: `src-frontend/src/hooks/useVoice.ts` (MediaRecorder + TTS playback)
- Create: `src-frontend/src/api/tauri.ts` (invoke wrappers)
- Create: `src-frontend/src/store/chatStore.ts` (Zustand: messages, session, streaming state)
- Modify: `src-frontend/src/App.tsx`, `main.tsx`, `index.css` (Tailwind)

**Step 1-5: Implement with component-driven development**

```tsx
// src-frontend/src/components/MessageBubble.tsx
interface MessageBubbleProps {
  message: Message;
  isStreaming?: boolean;
}

export function MessageBubble({ message, isStreaming }: MessageBubbleProps) {
  return (
    <div className={`flex gap-3 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
      <div className={`max-w-[70%] p-3 rounded-2xl ${
        message.role === 'user' ? 'bg-blue-600 text-white rounded-tr-none' :
        message.role === 'assistant' ? 'bg-gray-800 text-white rounded-tl-none' :
        'bg-amber-900/50 text-amber-100 rounded-br-none'
      }`}>
        <ReactMarkdown components={{ code: CodeBlock }}>
          {message.content}
        </ReactMarkdown>
        {message.toolCalls && message.toolCalls.map(tc => (
          <ToolResultCard key={tc.id} toolCall={tc} />
        ))}
        {isStreaming && <span className="animate-pulse text-gray-400">▌</span>}
      </div>
    </div>
  );
}
```

---

### Task 8: Tauri Backend Commands & IPC

**Objective:** Expose Python backend via Tauri commands; wire up FastAPI ↔ Tauri IPC.

**Files:**
- Create: `src-tauri/src-tauri/src/commands/chat.rs` (invoke Python API)
- Create: `src-tauri/src-tauri/src/commands/voice.rs` (STT/TTS)
- Create: `src-tauri/src-tauri/src/commands/tools.rs` (tool execution)
- Create: `src-tauri/src-tauri/src/commands/memory.rs` (history, search)
- Create: `src-tauri/src-tauri/src/python_sidecar.rs` (spawn/manage Python process)
- Modify: `src-tauri/src-tauri/src/main.rs` (register commands)
- Create: `src-python/main.py` (FastAPI app with `/chat`, `/voice`, `/tools`, `/memory` routes)

**Step 1-5: Implement**

```rust
// src-tauri/src-tauri/src/commands/chat.rs
#[tauri::command]
pub async fn send_message(session_id: String, content: String) -> Result<StreamingResponse, String> {
    let client = reqwest::Client::new();
    let resp = client
        .post("http://127.0.0.1:8765/chat/stream")
        .json(&json!({ "session_id": session_id, "content": content }))
        .send()
        .await
        .map_err(|e| e.to_string())?;
    
    // Return stream as Tauri event stream
    Ok(StreamingResponse::from(resp))
}
```

```python
# src-python/main.py
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from src_python.agent.core import Agent
from src_python.config import Config

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

config = Config()
agent = Agent(config)

@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    async def generate():
        async for chunk in agent.chat_stream(request.content, request.session_id):
            yield f"data: {chunk.json()}\n\n"
    return StreamingResponse(generate(), media_type="text/event-stream")

@app.post("/voice/stt")
async def voice_stt(audio: UploadFile):
    text = await stt_engine.transcribe(audio.file)
    return {"text": text}

@app.post("/voice/tts")
async def voice_tts(request: TTSRequest):
    audio_bytes = await tts_engine.synthesize(request.text)
    return Response(content=audio_bytes, media_type="audio/mpeg")
```

---

### Task 9: Voice Integration (Frontend + Backend)

**Objective:** Push-to-talk STT, streaming TTS playback, visual feedback.

**Files:**
- Create: `src-python/voice/stt.py` (faster-whisper)
- Create: `src-python/voice/tts.py` (edge-tts)
- Create: `src-frontend/src/hooks/useVoice.ts` (MediaRecorder, AudioContext)
- Create: `src-frontend/src/components/WaveformVisualizer.tsx`

---

## Phase 4: Kanban Integration & Daily Progress (Ongoing)

### Task 10: Kanban Task Setup

**Objective:** Create kanban tasks for each implementation task above.

```bash
# Run once per task:
hermes kanban create "Task N: <Title>" \
  --workspace "dir:C:/Projects/JARVIS-Assistant" \
  --skill software-development/plan \
  --assignee coder
```

### Task 11: Daily Progress Logger

**Objective:** Auto-generate daily progress markdown from kanban + git.

**Files:**
- Create: `scripts/daily_progress.py`
- Cron job to run daily

---

## Verification Checklist

- [ ] All backends initialize without error
- [ ] Fallback works when primary is down
- [ ] Tool registry executes registered tools
- [ ] Memory persists across sessions
- [ ] CLI starts and accepts input
- [ ] Voice module works (if enabled)
- [ ] Daily progress script generates report

---

## Risks & Tradeoffs

| Risk | Mitigation |
|------|------------|
| RunPod cold starts add latency | Keep a warm instance or use serverless with min_workers=1 |
| 4GB VRAM limits local models | Use 4-bit quantized 3B/7B models only |
| Rate limits on free tiers | Multi-backend fallback design handles this |
| Skill review for third-party code | Stick to built-in skills; audit any external scripts |

---

## Open Questions

1. RunPod endpoint ready? Need to deploy vLLM first.
2. Which voice model for TTS? (edge-tts voices vs. local piper)
3. Need web search API key? (Brave, SerpAPI, or use browser-use)