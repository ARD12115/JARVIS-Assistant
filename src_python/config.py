import os
from dataclasses import dataclass, field
from typing import List
from dotenv import load_dotenv

# Load .env from project root (C:/Projects/JARVIS-Assistant)
# __file__ is src_python/config.py, so we need to go up 2 levels:
# config.py -> src_python -> JARVIS-Assistant (project root)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))


@dataclass
class Config:
    # LLM Backend Configuration
    primary_backend: str = os.getenv("PRIMARY_BACKEND", "nvidia_nim")
    openrouter_key: str = os.getenv("OPENROUTER_API_KEY", "")
    nvidia_nim_api_key: str = os.getenv("NVIDIA_NIM_API_KEY", "")
    nvidia_nim_base_url: str = os.getenv("NVIDIA_NIM_BASE_URL", "https://integrate.api.nvidia.com/v1")
    nvidia_nim_model: str = os.getenv("NVIDIA_NIM_MODEL", "nvidia/nemotron-3-super-120b-a12b")
    fallback_backends: List[str] = field(
        default_factory=lambda: [
            backend.strip()
            for backend in os.getenv("FALLBACK_BACKENDS", "openrouter").split(",")
            if backend.strip()
        ]
    )
    code_exec_enabled: bool = os.getenv("CODE_EXEC_ENABLED", "false").lower() == "true"

    # Application Configuration
    db_path: str = os.getenv("JARVIS_DB", "jarvis.db")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    voice_enabled: bool = os.getenv("VOICE_ENABLED", "false").lower() == "true"

    # FastAPI Server
    api_host: str = os.getenv("API_HOST", "0.0.0.0")
    api_port: int = int(os.getenv("PORT", os.getenv("API_PORT", "8765")))

    # External API Keys
    openweather_key: str = os.getenv("OPENWEATHER_API_KEY", "")
    brave_key: str = os.getenv("BRAVE_API_KEY", "")
    serpapi_key: str = os.getenv("SERPAPI_KEY", "")