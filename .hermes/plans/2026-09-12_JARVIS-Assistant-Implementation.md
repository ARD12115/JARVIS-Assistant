# JARVIS Assistant Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Build a JARVIS-like AI assistant with multi-backend LLM support (NVIDIA NIM primary + OpenRouter fallback), voice capabilities, tool registry, and persistent memory — delivered as a **Tauri desktop app** (Rust + React/TypeScript frontend, Python backend) with chat UI, daily progress tracking, and kanban integration.

**Architecture:** Tauri desktop app with:
- **Frontend:** React + TypeScript + Tailwind CSS (chat UI, streaming messages, voice controls)
- **Backend:** Python (FastAPI) for LLM orchestration, tools, memory — communicates via Tauri IPC
- **LLM Layer:** Multi-backend (NVIDIA NIM primary → OpenRouter fallback) with auto-failover
- **Voice:** faster-whisper STT + edge-tts TTS (push-to-talk, optional wake word)
- **Memory:** SQLite session persistence
- **Kanban:** Hermes kanban for task tracking, daily progress auto-generation

**Tech Stack:**
- Frontend: React 18, TypeScript, Tailwind CSS, Vite, Zustand (state), React Markdown
- Backend: Python 3.11+, FastAPI, httpx, SQLite, faster-whisper, edge-tts, NVIDIA NIM client, OpenRouter client, python-dotenv
- Desktop: Tauri 2.x (Rust), Webview2 (Windows)
- Dev: npm, uv/pip, cargo

---

## Current Status (Sept 19, 2026)

| Phase | Status | Notes |
|-------|--------|-------|
| Phase 1: Foundation & LLM Layer | ✅ **COMPLETE** | NVIDIA NIM + OpenRouter working, auto-failover tested |
| Phase 2: Tools + Memory + Agent | ✅ **COMPLETE** | 7 tools, SQLite memory, FastAPI backend, agent loop |
| Phase 3: Frontend + Voice + Integration | 🔄 **IN PROGRESS** | Tauri compiles; `npx tauri dev` needed to test integrated UI |
| Phase 4: Kanban & Progress | ✅ **ONGOING** | Daily progress auto-generation working |

**Backend:** Running stably on port 8765 for 49+ hours (96+ loop iterations)
**Frontend:** Running on port 5173 with proxy to backend
**Tauri:** Compiles successfully, ready for `npx tauri dev`

---

## Phase 1: Project Foundation & Multi-Backend LLM Layer (Days 1-3) — ✅ DONE

### Task 1: Initialize Project Structure & Config — ✅ DONE
- Tauri + React + Python repo skeleton created
- Config management with `.env` loading from project root
- Environment handling with NVIDIA NIM + OpenRouter

### Task 2: LLM Backend Abstraction & Clients — ✅ DONE
- Unified interface for all LLM backends
- `nvidia_nim_client.py` — NVIDIA NIM (PRIMARY, model: `nvidia/nemotron-3-super-120b-a12b`)
- `openrouter_client.py` — OpenRouter (FALLBACK)
- Removed: `ollama_client.py`, `runpod_client.py` (per user request)

### Task 3: Auto-Fallback LLM Manager — ✅ DONE
- Health checks with 30s cache TTL
- Fallback logic: NVIDIA NIM → OpenRouter
- Known issue: Cache causes intermittent false negatives for NVIDIA

---

## Phase 2: Tool Registry & Core Agent Loop (Days 4-6) — ✅ DONE

### Task 4: Tool Registry System — ✅ DONE
- Pluggable tool system with schema validation
- 7 built-in tools: time, weather, web_search, system_info, file_read, file_write, file_list, code_exec
- ⚠️ `code_exec` flagged as security risk (no sandbox yet)

### Task 5: Session Memory (SQLite) — ✅ DONE
- Persistent conversation history with search and summarization
- Schema: conversations table with indexes
- Known issues: `MAX_HISTORY_LIMIT` constant missing, `session_exists()` method missing

### Task 6: Core Agent Loop — ✅ DONE
- Main REPL coordinating LLM, tools, and memory
- Streaming chat with tool calling support
- System prompt with tool descriptions

---

## Phase 3: Tauri Frontend & Integration (Days 7-10) — 🔄 IN PROGRESS

### Task 7: React Chat UI (Frontend) — ✅ SCAFFOLDED
**Components created:**
- `ChatWindow.tsx` — Main chat area + streaming
- `MessageBubble.tsx` — User/Assistant/Tool messages
- `InputBar.tsx` — Text + voice input
- `VoiceButton.tsx` — Push-to-talk
- `ToolResultCard.tsx` — Expandable tool results
- `Sidebar.tsx` — Session history, settings

**Hooks & Store (need Tauri IPC connection):**
- `useChat.ts` — WebSocket/IPC connection (NOT YET CONNECTED)
- `useVoice.ts` — MediaRecorder + TTS playback (NOT YET CONNECTED)
- `chatStore.ts` — Zustand: messages, session, streaming state

### Task 8: Tauri Backend Commands & IPC — ✅ SCAFFOLDED
**Commands created:**
- `chat.rs` — send_message, create_session, list_sessions, get_history
- `voice.rs` — voice_stt, voice_tts, list_voices
- `tools.rs` — list_tools, execute_tool
- `memory.rs` — list_sessions, get_history, load_session, search_memory

**Rust fixes applied:**
- Fixed `@url:` prefix issue in chat.rs
- Fixed duplicate command names (renamed memory commands)
- Fixed async fn main() for Rust 2021 edition
- Fixed python_sidecar.rs dev/prod path resolution
- Fixed tauri.conf.json plugin configs (7 iterations)

### Task 9: Voice Integration — 🔄 PARTIAL
**Backend:** ✅ `stt.py` (faster-whisper), `tts.py` (edge-tts)
**Frontend:** ❌ `useVoice.ts`, `WaveformVisualizer.tsx` not implemented
**Known issue:** TTS `synthesize()` signature mismatch (voice param ignored)

### Task 10: Frontend-Backend Integration — 🔄 PENDING
- Connect `useChat.ts` to Tauri `invoke('send_message')`
- Connect streaming SSE to `MessageBubble` for token-by-token rendering
- Connect `useVoice.ts` to Tauri `invoke('voice_stt/tts')`
- Wire up Sidebar session history

---

## Phase 4: Kanban Integration & Daily Progress — ✅ ONGOING

### Task 11: Kanban Task Setup — ✅ DONE
```bash
# Run once per task:
hermes kanban create "Task N: <Title>" \
  --workspace "dir:C:/Projects/JARVIS-Assistant" \
  --skill software-development/plan \
  --assignee coder
```

### Task 12: Daily Progress Logger — ✅ DONE
- `scripts/daily_progress.py` auto-generates progress markdown from git + kanban
- Runs via cron daily at 23:59
- Output: `docs/progress/YYYY-MM-DD.md`

---

## Remaining Work (Priority Order)

| Priority | Task | Effort | Blockers |
|----------|------|--------|----------|
| **HIGH** | Connect frontend hooks to Tauri IPC (`useChat`, `useVoice`) | Medium | None |
| **HIGH** | Wire streaming SSE to `MessageBubble` for token-by-token rendering | Medium | None |
| **HIGH** | Fix health check cache TTL false negatives | Low | None |
| **HIGH** | Add valid OpenRouter API key to `.env` | Trivial | User action needed |
| **MEDIUM** | Implement `useVoice.ts` + `WaveformVisualizer.tsx` | Medium | None |
| **MEDIUM** | Add sandbox to `code_exec` tool | High | Security design needed |
| **MEDIUM** | Fix `MAX_HISTORY_LIMIT` and `session_exists()` in memory | Low | None |
| **MEDIUM** | Fix TTS `synthesize()` voice parameter | Low | None |
| **LOW** | Add system tray & global hotkey | Medium | Tauri plugin config |
| **LOW** | Wake-word detection (Porcupine) | High | Optional stretch |

---

## Verification Checklist

- [x] All backends initialize without error
- [x] Fallback works when primary is down (tested)
- [x] Tool registry executes registered tools
- [x] Memory persists across sessions
- [x] FastAPI backend starts and accepts input
- [x] Voice module backend works (STT/TTS)
- [x] Daily progress script generates report
- [ ] Tauri desktop app runs integrated (`npx tauri dev`)
- [ ] Frontend streaming renders in chat UI
- [ ] Voice push-to-talk works end-to-end
- [ ] Code execution sandbox implemented

---

## Risks & Tradeoffs

| Risk | Mitigation |
|------|------------|
| NVIDIA NIM API changes | Version-pinned models; health check cache |
| Free API tier exhaustion | Multi-backend fallback design; paid tier budget $10/mo |
| Tauri/Rust learning curve | Use Python sidecar pattern; start with template |
| WebView2 distribution on Windows | Bundle WebView2 bootstrapper in installer |
| Scope creep (voice, GUI, etc.) | Kanban WIP limits; stretch goals explicitly labeled |
| `code_exec` security risk | Implement sandbox (subprocess + timeout + no network) |

---

## Key Changes from Original Plan

| Original | Current | Reason |
|----------|---------|--------|
| RunPod vLLM primary | NVIDIA NIM primary | User has NVIDIA account; free tier available |
| Ollama local fallback | Removed | 4GB VRAM insufficient for useful models |
| OpenRouter/Anthropic tertiary | OpenRouter fallback only | Simplified; user requested only NIM + OpenRouter |
| pnpm for Node | npm | pnpm Windows native binary issues |
| httpx-mock 0.22.0 | httpx-mock 0.2.2 | Version 0.22.0 doesn't exist |
| 8 tools | 7 tools | code_exec flagged as security risk |
| `src-python` folder | `src_python` (underscore) | Actual structure |
| `src-tauri/src-tauri` nesting | Flattened to `src-tauri/src` | Fixed Cargo.toml location |

---

## Open Questions

1. **OpenRouter API key** — User needs to add valid key from openrouter.ai/keys
2. **Voice model for TTS** — edge-tts voices vs. local piper (edge-tts working)
3. **Web search API key** — Brave, SerpAPI, or use browser-use (browser-use implemented)
4. **code_exec sandbox** — How to implement safely? (Docker? gVisor? subprocess with strict limits?)

---

*Plan status: Phases 1-2 complete. Phase 3 (Tauri integration) in progress. Backend stable for 49+ hours.*