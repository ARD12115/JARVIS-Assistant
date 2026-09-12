import time
from typing import List, AsyncGenerator
from src_python.llm.base import LLMBackend, Message, ChatResponse, ChatStreamChunk
from src_python.llm.factory import create_all_backends
from src_python.config import Config


class AllBackendsFailedError(Exception):
    pass


class LLMManager:
    def __init__(self, config: Config):
        self.config = config
        self.backends = create_all_backends(config)
        self._health_cache = {}
        self._cache_ttl = 30  # seconds

    def _is_healthy(self, backend: LLMBackend) -> bool:
        now = time.time()
        backend_name = backend.__class__.__name__
        if backend_name in self._health_cache:
            cached, timestamp = self._health_cache[backend_name]
            if now - timestamp < self._cache_ttl:
                return cached
        healthy = backend.is_available()
        self._health_cache[backend_name] = (healthy, now)
        return healthy

    def get_healthy_backend(self) -> LLMBackend:
        for backend in self.backends:
            if self._is_healthy(backend):
                return backend
        # Last resort: return first anyway
        if self.backends:
            return self.backends[0]
        raise AllBackendsFailedError("No LLM backends configured")

    def get_status(self) -> dict:
        return {
            backend.__class__.__name__: {
                "healthy": self._is_healthy(backend),
                "models": backend.get_models()
            }
            for backend in self.backends
        }

    def chat(self, messages: List[Message], **kwargs) -> ChatResponse:
        last_error = None
        for backend in self.backends:
            if not self._is_healthy(backend):
                continue
            try:
                return backend.chat(messages, **kwargs)
            except Exception as e:
                last_error = e
                print(f"Backend {backend.__class__.__name__} failed: {e}")
                # Invalidate health cache for this backend
                self._health_cache[backend.__class__.__name__] = (False, time.time())
        raise AllBackendsFailedError(f"All backends failed. Last error: {last_error}")

    async def chat_stream(self, messages: List[Message], **kwargs) -> AsyncGenerator[ChatStreamChunk, None]:
        last_error = None
        for backend in self.backends:
            if not self._is_healthy(backend):
                continue
            try:
                async for chunk in backend.chat_stream(messages, **kwargs):
                    yield chunk
                return  # Success - exit after first working backend
            except Exception as e:
                last_error = e
                print(f"Backend {backend.__class__.__name__} failed: {e}")
                # Invalidate health cache for this backend
                self._health_cache[backend.__class__.__name__] = (False, time.time())
        raise AllBackendsFailedError(f"All backends failed. Last error: {last_error}")