import httpx
from typing import List, AsyncGenerator
from src_python.llm.base import LLMBackend, Message, ChatResponse, ChatStreamChunk
from src_python.config import Config


class OllamaClient(LLMBackend):
    def __init__(self, config: Config):
        self.host = config.ollama_host.rstrip("/")
        self.model = config.ollama_model
        self.client = httpx.AsyncClient(timeout=120.0)

    def is_available(self) -> bool:
        try:
            resp = httpx.get(f"{self.host}/api/tags", timeout=5.0)
            return resp.status_code == 200
        except Exception:
            return False

    def get_models(self) -> List[str]:
        try:
            resp = httpx.get(f"{self.host}/api/tags", timeout=5.0)
            if resp.status_code == 200:
                return [m["name"] for m in resp.json().get("models", [])]
        except Exception:
            pass
        return [self.model]

    def chat(self, messages: List[Message], **kwargs) -> ChatResponse:
        import asyncio
        return asyncio.run(self._chat_async(messages, **kwargs))

    async def _chat_async(self, messages: List[Message], **kwargs) -> ChatResponse:
        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
            "options": {
                "temperature": kwargs.get("temperature", 0.7),
                "num_predict": kwargs.get("max_tokens", 2048),
            }
        }
        resp = await self.client.post(f"{self.host}/api/chat", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return ChatResponse(
            content=data["message"]["content"],
            model=data.get("model", self.model),
            usage={
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0)
            }
        )

    async def chat_stream(self, messages: List[Message], **kwargs) -> AsyncGenerator[ChatStreamChunk, None]:
        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": True,
            "options": {
                "temperature": kwargs.get("temperature", 0.7),
                "num_predict": kwargs.get("max_tokens", 2048),
            }
        }
        
        async with self.client.stream("POST", f"{self.host}/api/chat", json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if line.strip():
                    try:
                        import json
                        data = json.loads(line)
                        content = data.get("message", {}).get("content", "")
                        done = data.get("done", False)
                        if content:
                            yield ChatStreamChunk(content=content, done=False)
                        if done:
                            yield ChatStreamChunk(content="", done=True)
                    except Exception:
                        continue