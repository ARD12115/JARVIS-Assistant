# Product Requirements Document (PRD)
## JARVIS Assistant — AI Voice-Enabled Desktop Agent

---

### 1. Executive Summary

**Product Name:** JARVIS Assistant  
**Version:** 1.0 (Prototype)  
**Owner:** Abhinav Derla  
**Target Date:** September 30, 2026 (Yugma TechFest 2026 deadline)  
**Status:** Active Development — Backend stable for 49+ hours, ready for Tauri integration  

JARVIS is a JARVIS-inspired AI assistant that runs as a **native desktop application** (Tauri 2.x) with a React/TypeScript chat UI. It provides a conversational interface with tool-use capabilities (web search, system control, file operations), persistent memory across sessions, and voice I/O (push-to-talk STT + TTS). The multi-backend LLM architecture (NVIDIA NIM primary → OpenRouter fallback) ensures resilience against rate limits and outages. Daily progress tracking via Hermes kanban for portfolio documentation.

---

### 2. Problem Statement

Current AI assistants suffer from:
- **Single-point-of-failure APIs** — rate limits, outages, and quotas block workflow
- **No local fallback** — offline = useless
- **Stateless sessions** — context lost between restarts
- **Closed ecosystems** — hard to extend with custom tools
- **Web-only or CLI-only** — no native desktop experience with voice
- **No progress visibility** — can't demonstrate day-by-day development for hackathons/portfolios

---

### 3. Target Users

| Persona | Needs |
|---------|-------|
| Developer (self) | Native desktop app, multi-backend LLM, tool registry, daily logs for portfolio |
| Hackathon judges | Working desktop demo, visible progress, technical depth |
| Future collaborators | Clean architecture, documented APIs, kanban-tracked tasks |

---

### 4. Core Features (MVP — Prototype)

| ID | Feature | Priority | Description |
|----|---------|----------|-------------|
| F1 | Multi-Backend LLM Layer | P0 | NVIDIA NIM (primary) → OpenRouter (fallback) with auto-failover |
| F2 | Tool Registry | P0 | Pluggable tools: time, weather, web search, system info, file ops, code execution |
| F3 | Persistent Session Memory | P0 | SQLite-backed conversation history, search, summarization, cross-session recall |
| F4 | Native Desktop Chat UI | P0 | Tauri + React + TypeScript: streaming messages, markdown, code blocks, tool cards, sidebar history |
| F5 | Voice I/O | P1 | Push-to-talk STT (faster-whisper) + TTS (edge-tts), waveform visualizer, optional wake word |
| F6 | Kanban Integration | P0 | Auto-task creation, daily progress markdown generator, git commit linking |
| F7 | Config & Secrets Management | P0 | `.env`-based, profile-aware, no hardcoded keys |
| F8 | System Tray & Global Hotkey | P2 | Minimize to tray, global push-to-talk hotkey |

---

### 5. User Stories

| ID | Story | Acceptance Criteria |
|----|-------|---------------------|
| US1 | As a developer, I want JARVIS to answer questions using the best available LLM | Primary backend responds <3s; falls back automatically if primary fails |
| US2 | As a developer, I want to ask "what's the weather" and get real data | Tool registry executes weather tool, returns formatted result card in chat |
| US3 | As a developer, I want my conversation history to persist | Restart app → previous sessions available in sidebar |
| US4 | As a hackathon participant, I want daily progress logs auto-generated | Run `python scripts/daily_progress.py` → `docs/progress/YYYY-MM-DD.md` created |
| US5 | As a user, I want to talk to JARVIS | Hold hotkey → speak → JARVIS replies in voice with waveform animation |
| US6 | As a user, I want JARVIS to run code and show results | Ask "run this python" → tool executes → result rendered in chat |

---

### 6. Non-Functional Requirements

| Category | Requirement |
|----------|-------------|
| Performance | App cold start <2s; LLM response streaming token-by-token; voice latency <1.5s |
| Reliability | 99% uptime for local components; graceful degradation when backends fail |
| Security | API keys only in `.env` (gitignored); no secrets in code or logs; tool sandbox |
| Extensibility | New tools in <50 lines Python; new LLM backends in <100 lines; React components for UI |
| Portability | Windows (WebView2), Linux (WebKitGTK), macOS (WebKit); Python 3.11+ |
| Observability | Structured logging (JSON), per-request latency metrics, Tauri devtools |

---

### 7. Success Metrics (Prototype)

| Metric | Target |
|--------|--------|
| Backend failover time | <2 seconds |
| Tool execution success rate | >95% |
| Memory recall accuracy | 100% for last 50 turns |
| Daily progress log generation | Automated, zero manual steps |
| Code coverage (core modules) | >80% |
| App bundle size | <150MB |
| Voice round-trip latency | <2s (STT + LLM + TTS) |

---

### 8. Out of Scope (v1.0)

- Mobile app (iOS/Android)
- Multi-user / server deployment / cloud sync
- Fine-tuning / custom model training
- Plugin marketplace
- Wake-word detection (Porcupine/Picovoice) — stretch only
- Advanced RAG / document ingestion — v1.1
- Ollama / RunPod backends (removed per user request — keep NIM + OpenRouter only)

---

### 9. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| NVIDIA NIM API changes | Low | Medium | Version-pinned models; health check cache |
| 4GB VRAM too small for useful local model | N/A | N/A | Local Ollama removed; NIM runs in cloud |
| Free API tier exhaustion | Medium | High | Multi-backend design; paid tier budget $10/mo |
| Tauri/Rust learning curve | Medium | Medium | Start with template; use Python sidecar pattern |
| WebView2 distribution on Windows | Low | High | Bundle WebView2 bootstrapper in installer |
| Scope creep (voice, GUI, etc.) | High | Medium | Kanban WIP limits; stretch goals explicitly labeled |

---

### 10. Timeline (Prototype)

| Week | Focus | Deliverable |
|------|-------|-------------|
| 1 (Sep 12-18) | Foundation + LLM Layer | Tauri+React+Python scaffold, NIM + OpenRouter backends, auto-fallback working ✅ **DONE** |
| 2 (Sep 19-25) | Tools + Memory + Agent Core | 7 tools, SQLite memory, FastAPI backend, agent loop ✅ **DONE** |
| 3 (Sep 26-30) | Frontend + Voice + Integration | Chat UI, streaming, voice, Tauri commands, demo script, README |

**Current State (Sep 19, 2026):** Phases 1-2 complete. Backend running stably for 49+ hours. Phase 3 in progress — Tauri desktop app compiles, needs `npx tauri dev` to test integrated UI.

---

### 11. Appendix: Daily Progress Tracking Format

Each day produces `docs/progress/YYYY-MM-DD.md`:

```markdown
# Daily Progress — YYYY-MM-DD

## Completed
- [ ] Task N: Title — `git commit abc123`

## In Progress
- Task N+1: Title — 60% done

## Blockers
- None / Description

## Next Steps
- Task N+1 completion
- Task N+2 start

## Metrics
- Lines added: XX
- Tests passing: YY/ZZ
- Backend latency (avg): XXms
```