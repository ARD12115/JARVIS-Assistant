# JARVIS Assistant

A JARVIS-inspired AI desktop assistant with multi-backend LLM support, tool registry, persistent memory, and voice I/O. Built with **Tauri 2.x + React/TypeScript + Python**.

## ✨ Features

- **Multi-Backend LLM** — NVIDIA NIM (primary) → OpenRouter (fallback) with auto-failover
- **7 Built-in Tools** — Web search, weather, system info, file ops, code execution, time
- **Persistent Memory** — SQLite sessions with search & summarization
- **Native Desktop UI** — Streaming chat, markdown/code rendering, tool result cards, session sidebar
- **Voice I/O** — Push-to-talk STT (faster-whisper) + TTS (edge-tts)
- **Kanban Integration** — Hermes kanban for task tracking, auto daily progress logs

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  React Frontend (WebView)  ◄── Tauri IPC  ►  Rust Commands  │
│  - ChatWindow, MessageBubble                              │
│  - InputBar (text + voice)                                │
│  - Sidebar (sessions)                                     │
└────────────────────────────────┬────────────────────────────┘
                                 │ HTTP (localhost:8765)
                                 ▼
┌─────────────────────────────────────────────────────────────┐
│  Python FastAPI Sidecar                                    │
│  - LLM Manager (NVIDIA NIM + OpenRouter + failover)       │
│  - Tool Registry (7 tools, extensible)                     │
│  - Session Memory (SQLite)                                 │
│  - Voice: faster-whisper STT + edge-tts TTS                │
└─────────────────────────────────────────────────────────────┘
```

## Current Status (Sept 2026)

| Component | Status |
|-----------|--------|
| Python Backend | ✅ Running (port 8765, 49+ hrs stable) |
| Frontend (Vite) | ✅ Running (port 5173) |
| Tauri App | ✅ Compiles (`npx tauri dev` ready) |
| NVIDIA NIM | ✅ Working (`nemotron-3-super-120b-a12b`) |
| OpenRouter | ⚠️ Placeholder key (needs valid key) |

## 🚀 Quick Start

### Prerequisites
- **Rust 1.75+** • **Node 20+ (npm)** • **Python 3.11+ (uv)**

### Setup

```bash
# 1. Configure environment
cp .env.example .env
# Edit .env with your API keys (NVIDIA NIM, OpenRouter, OpenWeather, etc.)

# 2. Python backend
cd src_python && uv venv && uv pip install -e .[dev]
uvx browser-use install

# 3. Frontend
cd ../src-frontend && npm install

# 4. Run all (2 terminals)
# Terminal 1: Frontend dev server
cd src-frontend && npm run dev

# Terminal 2: Tauri app (starts and manages the Python sidecar)
cd src-tauri && npm run tauri dev
```

### Production Build

```bash
cd src-tauri && npm run tauri build
# Output: src-tauri/target/release/bundle/
```

## 📁 Project Structure

```
JARVIS-Assistant/
├── docs/                    # PRD, TRD, Skills reference
├── scripts/                 # daily_progress.py (auto git log → markdown)
├── src_python/              # FastAPI backend
│   ├── llm/                 # NVIDIA NIM + OpenRouter clients + manager
│   ├── tools/               # Tool registry + 7 built-ins
│   ├── memory/              # SQLite session memory
│   ├── agent/               # Core agent loop
│   └── voice/               # STT/TTS engines
├── src-frontend/            # React + TS + Tailwind
│   └── src/components/      # ChatWindow, MessageBubble, InputBar, Sidebar
└── src-tauri/               # Tauri 2.x + Rust
    └── src/commands/        # IPC: chat, voice, tools, memory
```

## ⚙️ Configuration (`.env`)

```env
# LLM Backends
PRIMARY_BACKEND=nvidia_nim
NVIDIA_NIM_API_KEY=nvapi-xxx
NVIDIA_NIM_MODEL=nvidia/nemotron-3-super-120b-a12b
OPENROUTER_API_KEY=sk-or-xxx

# Tools
OPENWEATHER_API_KEY=xxx
BRAVE_API_KEY=xxx

# App
VOICE_ENABLED=true
API_PORT=8765
```

## 📋 Development Workflow

```bash
# Start kanban gateway (separate terminal)
hermes gateway start

# View/claim tasks
hermes kanban list
hermes kanban claim <task-id>

# Daily progress (auto-runs via cron)
python scripts/daily_progress.py
```

## 📚 Documentation

| File | Purpose |
|------|---------|
| `docs/PRD_JARVIS_Assistant.md` | Product requirements & user stories |
| `docs/TRD_JARVIS_Assistant.md` | Technical spec: APIs, data flows, deployment |
| `docs/SKILLS_JARVIS_Assistant.md` | Recommended Hermes skills & libraries |
| `.hermes/plans/...` | TDD implementation tasks |
| `FOLDER_STRUCTURE.md` | Complete directory tree |
| `requirements.txt` | All deps (Python/Node/Rust/System) |

## 🧪 Testing

```bash
# Python
cd src_python && uv run pytest -v --tb=short

# Frontend
cd src-frontend && npm test

# Rust
cd src-tauri && cargo test
```

## 📄 License

MIT