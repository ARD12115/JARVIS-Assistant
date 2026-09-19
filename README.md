# JARVIS Assistant

A JARVIS-inspired AI desktop assistant with multi-backend LLM support (NVIDIA NIM primary, OpenRouter fallback), tool registry, persistent memory, and voice I/O. Built with Tauri 2.x, React, TypeScript, and Python.

## Features

- **Multi-Backend LLM**: NVIDIA NIM (primary) → OpenRouter (fallback) with automatic failover
- **Tool Registry**: 7 built-in tools for web search, weather, system info, file operations, code execution, time
- **Persistent Memory**: SQLite-backed conversation history with search and summarization
- **Native Desktop UI**: Tauri + React + TypeScript with streaming chat, markdown rendering, tool result cards
- **Voice I/O**: Push-to-talk STT (faster-whisper) + TTS (edge-tts) with waveform visualization
- **Kanban Integration**: Hermes kanban for task tracking, daily progress auto-generation
- **Cross-Platform**: Windows, macOS, Linux

## Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                    JARVIS Desktop App                        │
│  ┌─────────────────┐    ┌─────────────────────────────────┐ │
│  │  React Frontend │◄──►│      Tauri Commands (Rust)      │ │
│  │  (WebView)      │    │  - chat, voice, tools, memory   │ │
│  └────────┬────────┘    └──────────────┬──────────────────┘ │
│           │                              │                   │
│           ▼                              ▼                   │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │           Python Backend (FastAPI Sidecar)               │ │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────────┐   │ │
│  │  │  LLM    │ │  Tool   │ │ Memory  │ │   Voice     │   │ │
│  │  │ Manager │ │ Registry│ │ (SQLite)│ │  (STT/TTS)  │   │ │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────────┘   │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Current Status (as of Sept 2026)

| Component | Status | Notes |
|-----------|--------|-------|
| Python Backend | ✅ Running | Port 8765, PID stable for 49+ hours |
| Frontend (Vite) | ✅ Running | Port 5173, proxy to backend |
| Tauri App | ✅ Compiles | Ready for `npx tauri dev` |
| NVIDIA NIM | ✅ Working | Model: `nvidia/nemotron-3-super-120b-a12b` |
| OpenRouter | ⚠️ Placeholder | API key needed from openrouter.ai |
| Ollama | ❌ Removed | Per user request - keep only NIM + OpenRouter |
| RunPod | ❌ Removed | Per user request - keep only NIM + OpenRouter |

## Quick Start

### Prerequisites

- **Rust** 1.75+ (`rustup`)
- **Node.js** 20+ with **npm** (`corepack enable` or download from nodejs.org)
- **Python** 3.11+ with **uv** (`pip install uv`)

### Development Setup

```bash
# Clone and enter project
cd JARVIS-Assistant

# 1. Setup Python backend
cd src-python
uv venv
uv pip install -e .
cd ..

# 2. Setup Frontend
cd src-frontend
npm install
cd ..

# 3. Setup Tauri (Rust) - dependencies auto-download on first run
cd src-tauri
cd ..

# 4. Configure environment
cp .env.example .env
# Edit .env with your API keys (NVIDIA NIM, OpenRouter, OpenWeather, etc.)

# 5. Start development (3 terminals)

# Terminal 1: Python backend
cd src-python
PYTHONPATH="C:/Projects/JARVIS-Assistant/src-python" .venv/Scripts/python.exe main.py

# Terminal 2: Frontend dev server
cd src-frontend
npm run dev

# Terminal 3: Tauri app (starts and manages the Python sidecar)
cd src-tauri
npm run tauri dev
```

### Production Build

```bash
cd src-tauri
npm run tauri build
# Output: src-tauri/target/release/bundle/
```

## Configuration

Copy `.env.example` to `.env` and configure:

```env
# LLM Backends
PRIMARY_BACKEND=nvidia_nim
NVIDIA_NIM_API_KEY=your-nvidia-api-key
NVIDIA_NIM_MODEL=nvidia/nemotron-3-super-120b-a12b
OPENROUTER_API_KEY=your-openrouter-key

# Tools
OPENWEATHER_API_KEY=your-key
BRAVE_API_KEY=your-key

# App
VOICE_ENABLED=true
API_PORT=8765
```

## Project Structure

```text
JARVIS-Assistant/
├── .env.example              # Environment template
├── .gitignore
├── docs/
│   ├── PRD_JARVIS_Assistant.md      # Product Requirements
│   ├── TRD_JARVIS_Assistant.md      # Technical Requirements
│   ├── SKILLS_JARVIS_Assistant.md   # Recommended skills/tools
│   └── progress/                     # Daily progress logs
├── scripts/
│   └── daily_progress.py             # Auto-generate daily logs
├── src-python/                 # Python FastAPI Backend
│   ├── main.py                 # Entry point
│   ├── config.py               # Configuration
│   ├── llm/                    # LLM abstraction (NVIDIA NIM + OpenRouter)
│   ├── tools/                  # Tool registry & 7 built-in tools
│   ├── memory/                 # SQLite session memory
│   ├── agent/                  # Core agent loop
│   └── voice/                  # STT/TTS engines
├── src-frontend/               # React + TS + Tailwind
│   ├── src/
│   │   ├── components/         # ChatWindow, MessageBubble, InputBar, etc.
│   │   ├── hooks/              # useChat, useVoice (to connect Tauri IPC)
│   │   ├── store/              # Zustand state management
│   │   └── types/              # TypeScript interfaces
│   └── package.json
└── src-tauri/                  # Tauri 2.x Rust App
    ├── Cargo.toml
    ├── tauri.conf.json
    └── src/
        ├── main.rs             # App entry, sidecar management
        ├── python_sidecar.rs   # Python subprocess management
        └── commands/           # Tauri commands (chat, voice, tools, memory)
```

## Development Workflow

### Kanban Task Management

```bash
# Create tasks (run once per implementation task)
hermes kanban create "Task: Description" \
  --workspace "dir:C:/Projects/JARVIS-Assistant" \
  --skill software-development/plan \
  --assignee coder

# Start gateway (separate terminal)
hermes gateway start

# View tasks
hermes kanban list
```

### Daily Progress

```bash
# Manual generation
python scripts/daily_progress.py

# Auto via cron (runs at 23:59 daily)
0 23 * * * cd /Projects/JARVIS-Assistant && python scripts/daily_progress.py
```

### Testing

```bash
# Python tests
cd src-python && uv run pytest tests/ -v --tb=short

# Frontend tests
cd src-frontend && npm test

# Rust tests
cd src-tauri && cargo test
```

## LLM Backend Setup

### NVIDIA NIM (Primary - Recommended)

1. Create account at [NVIDIA NGC](https://ngc.nvidia.com)
2. Get API key from [NVIDIA NIM](https://build.nvidia.com)
3. Add to `.env`:
   ```env
   NVIDIA_NIM_API_KEY=nvapi-xxx
   NVIDIA_NIM_MODEL=nvidia/nemotron-3-super-120b-a12b
   ```
4. Available models: Check https://integrate.api.nvidia.com/v1/models

### OpenRouter (Fallback)

1. Get API key from [OpenRouter](https://openrouter.ai/keys)
2. Add to `.env`:
   ```env
   OPENROUTER_API_KEY=sk-or-xxx
   ```

## Voice Setup

```bash
# STT: faster-whisper (downloads model on first run ~1.5GB)
# TTS: edge-tts (no download needed, uses Microsoft voices)

# Enable in .env
VOICE_ENABLED=true
```

## Google Cloud Run Deployment

The Python API can be deployed as a private Cloud Run service. The Tauri desktop application continues to use its locally managed Python sidecar.

Prerequisites:
- Google Cloud CLI authenticated with an account that can manage the selected project
- Billing enabled on the Google Cloud project

From the repository root:

```bash
gcloud config set project YOUR_PROJECT_ID
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com
gcloud run deploy jarvis-api \
  --source . \
  --region us-central1 \
  --no-allow-unauthenticated
```

The deployment uses [Dockerfile](Dockerfile), binds to Cloud Run's `PORT`, and does not upload `.env` or local SQLite files. Configure runtime secrets through Secret Manager or Cloud Run environment variables; do not commit them.

Cloud Run's local filesystem is ephemeral, so `jarvis.db` is suitable only for temporary state. Use a managed database before relying on cloud-hosted conversation history across instances.

## Documentation

- [PRD](docs/PRD_JARVIS_Assistant.md) - Product Requirements
- [TRD](docs/TRD_JARVIS_Assistant.md) - Technical Specification
- [Skills & Tools](docs/SKILLS_JARVIS_Assistant.md) - Recommended Hermes skills and libraries
- [Implementation Plan](.hermes/plans/2026-09-12_JARVIS-Assistant-Implementation.md) - Detailed task breakdown

## License

MIT License - see LICENSE file for details.

## Acknowledgments

- [Tauri](https://tauri.app) - Desktop app framework
- [NVIDIA NIM](https://build.nvidia.com) - Optimized LLM inference
- [OpenRouter](https://openrouter.ai) - Unified LLM API
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) - Fast STT
- [edge-tts](https://github.com/rany2/edge-tts) - Free TTS
- [Hermes Agent](https://hermes-agent.nousresearch.com) - AI agent orchestration