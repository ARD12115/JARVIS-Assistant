# Recommended Skills & Tools for JARVIS Assistant

This document lists the best-fit Hermes skills, external tools, and libraries for building the JARVIS desktop assistant.

---

## Hermes Built-in Skills (Use These First)

### Project Planning & Execution
| Skill | Category | Purpose |
|-------|----------|---------|
| `software-development/plan` | Planning | Write detailed implementation plans to `.hermes/plans/` |
| `software-development/test-driven-development` | Development | Enforce RED-GREEN-REFACTOR cycle for all code |
| `software-development/refactor_workflow` | Development | Linear refactor workflow with checklists |
| `software-development/systematic-debugging` | Debugging | 4-phase root cause debugging |

### Autonomous Development
| Skill | Category | Purpose |
|-------|----------|---------|
| `autonomous-ai-agents/hermes-kanban-operations` | Kanban | Run autonomous kanban with gateway dispatcher, profile isolation |
| `autonomous-ai-agents/hermes-kanban-orchestration` | Kanban | Autonomous kanban dev with Hermes gateway dispatcher |
| `autonomous-ai-agents/kanban-gateway-orchestration` | Kanban | Fix kanban dispatcher using backup profile |

### Code Quality & Review
| Skill | Category | Purpose |
|-------|----------|---------|
| `software-development/requesting-code-review` | Review | Pre-commit review: security scan, quality gates, auto-fix |
| `code-review/python-code-review-optimization` | Review | Review and optimize Python modules |
| `software-development/simplify-code` | Refactor | Parallel 4-agent cleanup of recent code changes |

### Documentation & Research
| Skill | Category | Purpose |
|-------|----------|---------|
| `software-development/technical-documentation-overhaul` | Docs | Audit & rewrite project docs to match actual codebase |
| `research/grounded-citations` | Research | Ground answers in cited, verifiable sources |
| `research/arxiv` | Research | Search arXiv papers for ML/voice techniques |

### Productivity & Tracking
| Skill | Category | Purpose |
|-------|----------|---------|
| `productivity/session-librarian` | Sessions | Organize sessions by prompt: find, rename, archive, prune |
| `productivity/weekly-review-planning` | Planning | Weekly reset: commitments, stalled work, next-week plan |
| `productivity/meeting-action-items` | Tracking | Turn meeting notes into cited decisions, owners, tickets |

---

## External Tools & Libraries (Project Dependencies)

### Python Backend (`src-python/`)
```toml
# Core
fastapi = "^0.115.0"
uvicorn = "^0.32.0"
httpx = "^0.28.0"
pydantic = "^2.9.0"
pydantic-settings = "^2.5.0"
python-dotenv = "^1.0.0"
structlog = "^24.1.0"

# LLM Clients
openai = "^1.54.0"          # For OpenRouter/RunPod (OpenAI-compatible)
ollama = "^0.4.0"           # Official Ollama Python client

# Database
sqlalchemy = "^2.0.35"
aiosqlite = "^0.20.0"
alembic = "^1.13.0"

# Voice
faster-whisper = "^1.1.0"
edge-tts = "^6.1.0"

# System Tools
psutil = "^6.0.0"
GPUtil = "^1.4.0"

# Web Search (no API key)
browser-use = "^0.1.40"

# Testing
pytest = "^8.3.0"
pytest-asyncio = "^0.24.0"
pytest-cov = "^6.0.0"
httpx-mock = "^0.22.0"

# Dev Tools
ruff = "^0.6.0"
mypy = "^1.11.0"
pre-commit = "^3.8.0"
```

### Frontend (`src-frontend/`)
```json
{
  "dependencies": {
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "zustand": "^4.5.0",
    "react-markdown": "^9.0.0",
    "rehype-highlight": "^7.0.0",
    "lucide-react": "^0.441.0",
    "clsx": "^2.1.0",
    "tailwind-merge": "^2.5.0"
  },
  "devDependencies": {
    "@tauri-apps/api": "^2.0.0",
    "@tauri-apps/cli": "^2.0.0",
    "@vitejs/plugin-react": "^4.3.0",
    "typescript": "^5.5.0",
    "vite": "^5.4.0",
    "tailwindcss": "^3.4.0",
    "autoprefixer": "^10.4.0",
    "postcss": "^8.4.0",
    "vitest": "^2.0.0",
    "@testing-library/react": "^16.0.0",
    "eslint": "^9.0.0",
    "prettier": "^3.3.0"
  }
}
```

### Tauri/Rust (`src-tauri/`)
```toml
# Cargo.toml
[dependencies]
tauri = { version = "2.0", features = ["macros", "shell", "fs", "http", "process", "dialog", "clipboard-manager", "global-shortcut"] }
tauri-plugin-shell = "2.0"
tauri-plugin-fs = "2.0"
tauri-plugin-http = "2.0"
tauri-plugin-process = "2.0"
tauri-plugin-dialog = "2.0"
tauri-plugin-clipboard-manager = "2.0"
tauri-plugin-global-shortcut = "2.0"
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
tokio = { version = "1.0", features = ["full"] }
reqwest = { version = "0.12", features = ["json", "stream"] }
tracing = "0.1"
tracing-subscriber = { version = "0.3", features = ["env-filter", "json"] }
anyhow = "1.0"
thiserror = "1.0"
uuid = { version = "1.0", features = ["v4", "serde"] }
```

---

## Development Workflow Skills

### Daily Development Loop
1. **Morning**: `hermes kanban list` → pick task → `hermes kanban claim <id>`
2. **Plan**: Use `software-development/plan` to write task plan
3. **Implement**: Follow TDD (`software-development/test-driven-development`)
4. **Review**: `software-development/requesting-code-review` before commit
5. **Log**: `productivity/session-librarian` to organize session
6. **Evening**: `scripts/daily_progress.py` auto-generates progress markdown

### Kanban Commands (Run in Project Root)
```bash
# Create tasks (run once per implementation task)
hermes kanban create "Task 1: Initialize Project Structure" \
  --workspace "dir:C:/Projects/JARVIS-Assistant" \
  --skill software-development/plan \
  --assignee coder

# Start gateway (separate terminal)
hermes gateway start

# Check task status
hermes kanban list

# View task logs
cat ~/AppData/Local/hermes/kanban/logs/<task-id>.log
```

### Profile Management
```bash
# Configure kanban failure limit on backup profile (workers run here)
hermes config set kanban.failure_limit 20 --profile backup

# Copy skills to backup profile if needed
cp -r ~/AppData/Local/hermes/skills/* ~/AppData/Local/hermes/profiles/backup/skills/
```

---

## Voice & ML Specific Skills

| Skill | Use Case |
|-------|----------|
| `mlops-inference/background-training-monitor` | Monitor background model training if you fine-tune |
| `mlops/cross-hardware-ml-training` | Train on CUDA, infer on CUDA/DirectML/CPU auto-detect |
| `mlops-inference/llama-cpp` | Local GGUF inference as ultimate fallback |

---

## Recommended VS Code Extensions
```json
{
  "recommendations": [
    "tauri-apps.tauri-vscode",
    "rust-lang.rust-analyzer",
    "bradlc.vscode-tailwindcss",
    "esbenp.prettier-vscode",
    "dbaeumer.vscode-eslint",
    "ms-python.python",
    "ms-python.pylint",
    "charliermarsh.ruff",
    "mhutchie.git-graph",
    "eamodio.gitlens"
  ]
}
```

---

## Project-Specific Commands

### Start Development Environment
```bash
# Terminal 1: Python Backend
cd C:/Projects/JARVIS-Assistant/src-python
uv pip install -e .
uv run python main.py

# Terminal 2: Frontend Dev Server
cd C:/Projects/JARVIS-Assistant/src-frontend
pnpm dev

# Terminal 3: Tauri Dev
cd C:/Projects/JARVIS-Assistant/src-tauri
pnpm tauri dev
```

### Run Tests
```bash
# Python tests
cd src-python
uv run pytest tests/ -v --cov=src_python

# Frontend tests
cd src-frontend
pnpm test

# Rust tests
cd src-tauri/src-tauri
cargo test
```

### Build for Production
```bash
cd C:/Projects/JARVIS-Assistant/src-tauri
pnpm tauri build
# Output: src-tauri/src-tauri/target/release/bundle/
```

---

## Learning Resources (Bookmark These)

| Resource | Topic |
|----------|-------|
| [Tauri 2.x Guide](https://tauri.app/v2/guides/) | Desktop app development |
| [vLLM OpenAI API](https://docs.vllm.ai/en/latest/serving/openai_compatible_server.html) | Self-hosted LLM serving |
| [faster-whisper](https://github.com/SYSTRAN/faster-whisper) | Fast STT |
| [edge-tts](https://github.com/rany2/edge-tts) | Free TTS |
| [Zustand](https://github.com/pmndrs/zustand) | React state management |
| [React Markdown](https://github.com/remarkjs/react-markdown) | Markdown rendering |
| [Hermes Kanban](skills/autonomous-ai-agents/hermes-kanban-operations) | Task orchestration |

---

## Skill Gaps to Fill Later (Stretch)

| Capability | Skill to Create/Find |
|------------|---------------------|
| Tauri 2.x + Python sidecar pattern | Custom skill or template |
| React streaming chat components | Component library skill |
| faster-whisper + edge-tts integration | Voice pipeline skill |
| RunPod serverless deployment | Cloud deployment skill |
| WebView2 bundling for Windows | Distribution skill |

---

*Generated for JARVIS Assistant project — update as stack evolves.*