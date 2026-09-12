from src_python.llm.base import LLMBackend
from src_python.llm.runpod_client import RunPodClient
from src_python.llm.ollama_client import OllamaClient
from src_python.llm.openrouter_client import OpenRouterClient
from src_python.config import Config

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