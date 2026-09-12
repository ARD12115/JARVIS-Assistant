# JARVIS Assistant

A JARVIS-inspired AI desktop assistant with multi-backend LLM support, tool registry, persistent memory, and voice I/O. Built with Tauri 2.x, React, TypeScript, and Python.

## Features

- **Multi-Backend LLM**: RunPod vLLM (primary) → Ollama (local) → OpenRouter/Anthropic (fallback) with automatic failover
- **Tool Registry**: Extensible tools for web search, weather, system info, file operations, code execution
- **Persistent Memory**: SQLite-backed conversation history with search and summarization
- **Native Desktop UI**: Tauri + React + TypeScript with streaming chat, markdown rendering, tool result cards
- **Voice I/O**: Push-to-talk STT (faster-whisper) + TTS (edge-tts) with waveform visualization
- **Kanban Integration**: Hermes kanban for task tracking, daily progress auto-generation
- **Cross-Platform**: Windows, macOS, Linux

## Architecture

```
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

## Quick Start

### Prerequisites

- **Rust** 1.75+ (`rustup`)
- **Node.js** 20+ with **pnpm** (`corepack enable pnpm`)
- **Python** 3.11+ with **uv** (`pip install uv`)
- **Ollama** (for local LLM fallback): `curl -fsSL https://ollama.com/install.sh | sh`

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
pnpm install
cd ..

# 3. Setup Tauri (Rust)
cd src-tauri
# First run will download dependencies
cd ..

# 4. Configure environment
cp .env.example .env
# Edit .env with your API keys (RunPod, OpenRouter, OpenWeather, etc.)

# 5. Start development (3 terminals)
# Terminal 1: Python backend
cd src-python && uv run python main.py

# Terminal 2: Frontend dev server
cd src-frontend && pnpm dev

# Terminal 3: Tauri app
cd src-tauri && pnpm tauri dev
```

### Production Build

```bash
cd src-tauri
pnpm tauri build
# Output: src-tauri/src-tauri/target/release/bundle/
```

## Configuration

Copy `.env.example` to `.env` and configure:

```env
# LLM Backends
PRIMARY_BACKEND=runpod
RUNPOD_ENDPOINT=https://your-endpoint.runpod.io
RUNPOD_TOKEN=your-token
OLLAMA_MODEL=llama3.1:8b
OPENROUTER_API_KEY=your-key

# Tools
OPENWEATHER_API_KEY=your-key
BRAVE_API_KEY=your-key

# App
VOICE_ENABLED=true
API_PORT=8765
```

## Project Structure

```
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
│   ├── llm/                    # LLM backends (RunPod, Ollama, OpenRouter)
│   ├── tools/                  # Tool registry & built-in tools
│   ├── memory/                 # SQLite session memory
│   ├── agent/                  # Core agent loop
│   └── voice/                  # STT/TTS engines
├── src-frontend/               # React + TypeScript Frontend
│   ├── src/
│   │   ├── components/         # ChatWindow, MessageBubble, InputBar, etc.
│   │   ├── hooks/              # useChat, useVoice
│   │   ├── store/              # Zustand state management
│   │   └── types/              # TypeScript interfaces
│   └── package.json
└── src-tauri/                  # Tauri Rust App
    ├── Cargo.toml
    ├── tauri.conf.json
    └── src/
        ├── main.rs             # App entry, sidecar management
        ├── python_sidecar.rs   # Python process management
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
cd src-python && uv run pytest tests/ -v --cov=src_python

# Frontend tests
cd src-frontend && pnpm test

# Rust tests
cd src-tauri/src-tauri && cargo test
```

## LLM Backend Setup

### RunPod (Recommended Primary)

1. Create account at [RunPod](https://runpod.io)
2. Deploy vLLM serverless endpoint:
   ```bash
   # Model: meta-llama/Meta-Llama-3.1-8B-Instruct
   # GPU: A10 (24GB) or A100
   # Serverless with min_workers=1 for warm standby
   ```
3. Add endpoint URL and token to `.env`

### Ollama (Local Fallback)

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull model (4GB VRAM friendly)
ollama pull llama3.1:8b
# or for stronger reasoning:
ollama pull phi3.5:3.8b
```

### OpenRouter (Free Tier Fallback)

1. Get API key from [OpenRouter](https://openrouter.ai)
2. Add to `.env`

## Voice Setup

```bash
# STT: faster-whisper (downloads model on first run)
# TTS: edge-tts (no download needed, uses Microsoft voices)

# Enable in .env
VOICE_ENABLED=true
```

## Documentation

- [PRD](docs/PRD_JARVIS_Assistant.md) - Product Requirements
- [TRD](docs/TRD_JARVIS_Assistant.md) - Technical Specification
- [Skills & Tools](docs/SKILLS_JARVIS_Assistant.md) - Recommended Hermes skills and libraries
- [Implementation Plan](.hermes/plans/2026-09-12_JARVIS-Assistant-Implementation.md) - Detailed task breakdown

## License

MIT License - see LICENSE file for details.

## Acknowledgments

- [Tauri](https://tauri.app) - Desktop app framework
- [vLLM](https://vllm.ai) - Fast LLM inference
- [Ollama](https://ollama.com) - Local LLM runtime
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) - Fast STT
- [edge-tts](https://github.com/rany2/edge-tts) - Free TTS
- [Hermes Agent](https://hermes-agent.nousresearch.com) - AI agent orchestration