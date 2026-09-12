import os
from dataclasses import dataclass, field
from typing import List
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    # LLM Backend Configuration
    primary_backend: str = os.getenv("PRIMARY_BACKEND", "runpod")
    runpod_endpoint: str = os.getenv("RUNPOD_ENDPOINT", "")
    runpod_token: str = os.getenv("RUNPOD_TOKEN", "")
    ollama_host: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
    openrouter_key: str = os.getenv("OPENROUTER_API_KEY", "")
    anthropic_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    fallback_backends: List[str] = field(
        default_factory=lambda: os.getenv("FALLBACK_BACKENDS", "ollama,openrouter").split(",")
    )
    
    # Application Configuration
    db_path: str = os.getenv("JARVIS_DB", "jarvis.db")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    voice_enabled: bool = os.getenv("VOICE_ENABLED", "false").lower() == "true"
    
    # FastAPI Server
    api_host: str = os.getenv("API_HOST", "127.0.0.1")
    api_port: int = int(os.getenv("API_PORT", "8765"))
    
    # External API Keys
    openweather_key: str = os.getenv("OPENWEATHER_API_KEY", "")
    brave_key: str = os.getenv("BRAVE_API_KEY", "")
    serpapi_key: str = os.getenv("SERPAPI_KEY", "")