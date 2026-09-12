import httpx
from typing import List, AsyncGenerator
from src_python.llm.base import LLMBackend, Message, ChatResponse, ChatStreamChunk
from src_python.config import Config


class OpenRouterClient(LLMBackend):
    def __init__(self, config: Config):
        self.key = config.openrouter_key
        self.client = httpx.AsyncClient(
            base_url="https://openrouter.ai/api/v1",
            timeout=60.0,
            headers={"Authorization": f"Bearer {self.key}"} if self.key else {}
        )
        self.default_model = "meta-llama/llama-3.1-8b-instruct:free"

    def is_available(self) -> bool:
        return bool(self.key)

    def get_models(self) -> List[str]:
        return [self.default_model]

    def chat(self, messages: List[Message], **kwargs) -> ChatResponse:
        import asyncio
        return asyncio.run(self._chat_async(messages, **kwargs))

    async def _chat_async(self, messages: List[Message], **kwargs) -> ChatResponse:
        payload = {
            "model": kwargs.get("model", self.default_model),
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 2048),
            "stream": False,
        }
        resp = await self.client.post("/chat/completions", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return ChatResponse(
            content=data["choices"][0]["message"]["content"],
            model=data.get("model", self.default_model),
            usage=data.get("usage")
        )

    async def chat_stream(self, messages: List[Message], **kwargs) -> AsyncGenerator[ChatStreamChunk, None]:
        payload = {
            "model": kwargs.get("model", self.default_model),
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 2048),
            "stream": True,
        }
        
        async with self.client.stream("POST", "/chat/completions", json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        yield ChatStreamChunk(content="", done=True)
                        break
                    try:
                        import json
                        data = json.loads(data_str)
                        delta = data["choices"][0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield ChatStreamChunk(content=content, done=False)
                        if data["choices"][0].get("finish_reason"):
                            yield ChatStreamChunk(content="", done=True)
                    except Exception:
                        continue