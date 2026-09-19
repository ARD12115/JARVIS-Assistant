JARVIS-Assistant/
├── .env.example              # Environment template (copy to .env)
├── .gitignore
├── requirements.txt          # All dependencies (Python/Node/Rust/System)
├── README.md                 # Project documentation
├── README_SHORT.md           # Concise project overview
│
├── docs/                     # Documentation
│   ├── PRD_JARVIS_Assistant.md       # Product Requirements
│   ├── TRD_JARVIS_Assistant.md       # Technical Requirements
│   ├── SKILLS_JARVIS_Assistant.md    # Recommended skills & tools
│   └── progress/                     # Daily progress logs (auto-generated)
│       └── YYYY-MM-DD.md
│
├── scripts/                  # Automation scripts
│   └── daily_progress.py     # Generates daily progress from git
│
├── src_python/               # Python FastAPI Backend
│   ├── pyproject.toml        # Python project config
│   ├── main.py               # FastAPI entry point (all endpoints)
│   ├── config.py             # Multi-backend configuration (NVIDIA NIM + OpenRouter)
│   │
│   ├── llm/                  # LLM Abstraction Layer
│   │   ├── base.py           # Abstract LLMBackend interface
│   │   ├── manager.py        # Multi-backend manager with failover
│   │   ├── factory.py        # Backend factory
│   │   ├── nvidia_nim_client.py  # NVIDIA NIM client (PRIMARY)
│   │   └── openrouter_client.py  # OpenRouter client (FALLBACK)
│   │
│   ├── tools/                # Tool Registry System
│   │   ├── base.py           # Tool base class & registry
│   │   ├── __init__.py       # Tool registry factory
│   │   └── builtin/          # 7 Built-in Tools
│   │       ├── time_tool.py          # Get current time
│   │       ├── weather_tool.py       # Weather via OpenWeatherMap
│   │       ├── web_search_tool.py    # Web search (browser-use/Brave/SerpAPI)
│   │       ├── system_info_tool.py   # CPU/RAM/GPU/Disk info
│   │       ├── file_tools.py         # Read/Write/List files
│   │       └── code_exec_tool.py     # Sandboxed Python execution (⚠️ no sandbox yet)
│   │
│   ├── memory/               # Session Memory (SQLite)
│   │   ├── models.py         # Data models
│   │   └── session.py        # SessionMemory class (CRUD, search, summarize)
│   │
│   ├── agent/                # Core Agent Loop
│   │   ├── prompts.py        # System prompt template
│   │   └── core.py           # Agent class (streaming + tool calling)
│   │
│   └── voice/                # Voice I/O
│       ├── stt.py            # faster-whisper STT
│       └── tts.py            # edge-tts TTS (voice param issue: ignored)
│
├── src-frontend/             # React + TypeScript Frontend
│   ├── package.json
│   ├── vite.config.ts        # Vite + proxy to localhost:8765
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   ├── index.html
│   │
│   └── src/
│       ├── main.tsx          # React entry
│       ├── App.tsx           # Main app with sidebar
│       ├── index.css         # Tailwind + custom styles
│       │
│       ├── components/       # UI Components
│       │   ├── ChatWindow.tsx      # Main chat area + streaming
│       │   ├── MessageBubble.tsx   # User/Assistant/Tool messages
│       │   ├── InputBar.tsx        # Text + voice input
│       │   ├── Sidebar.tsx         # Session history
│       │   └── ToolResultCard.tsx  # Expandable tool results
│       │
│       ├── hooks/            # Custom React hooks
│       │   └── (useChat, useVoice - TO BE IMPLEMENTED)
│       │
│       ├── store/            # Zustand state management
│       │   └── chatStore.ts        # Messages, sessions, streaming
│       │
│       ├── api/              # Tauri IPC wrappers
│       │   └── tauri.ts
│       │
│       └── types/            # TypeScript interfaces
│           └── index.ts
│
└── src-tauri/                # Tauri 2.x Rust Desktop App
    ├── Cargo.toml
    ├── tauri.conf.json       # Tauri configuration (minimal, valid)
    │
    └── src/
        ├── main.rs           # App entry + Python sidecar lifecycle
        ├── python_sidecar.rs # Python subprocess management (dev/prod paths)
        │
        └── commands/         # Tauri Commands (IPC)
            ├── chat.rs       # send_message, create_session, list_sessions, get_history
            ├── voice.rs      # voice_stt, voice_tts, list_voices
            ├── tools.rs      # list_tools, execute_tool
            └── memory.rs     # list_sessions, get_history, load_session, search_memory

## Notes on Actual vs Planned Structure

| Planned | Actual | Status |
|---------|--------|--------|
| `ollama_client.py` | Removed | ✅ Per user request |
| `runpod_client.py` | Removed | ✅ Per user request |
| `anthropic_client.py` | Never created | ✅ Not needed |
| pnpm | npm | ✅ Windows binary issues |
| `src-python` folder name | `src_python` | Note: underscore in actual |
| `src-tauri/src-tauri` nesting | Flattened to `src-tauri/src` | Fixed |
| 8 tools | 7 tools | code_exec flagged as security risk |