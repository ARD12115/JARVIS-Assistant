import httpx
from typing import List, AsyncGenerator
from src_python.llm.base import LLMBackend, Message, ChatResponse, ChatStreamChunk
from src_python.config import Config


class RunPodClient(LLMBackend):
    def __init__(self, config: Config):
        self.endpoint = config.runpod_endpoint.rstrip("/")
        self.token = config.runpod_token
        self.client = httpx.AsyncClient(timeout=60.0)
        self.default_model = "meta-llama/Meta-Llama-3.1-8B-Instruct"

    def is_available(self) -> bool:
        if not self.endpoint or not self.token:
            return False
        try:
            resp = httpx.get(f"{self.endpoint}/health", timeout=5.0)
            return resp.status_code == 200
        except Exception:
            return False

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
        headers = {"Authorization": f"Bearer {self.token}"}
        resp = await self.client.post(f"{self.endpoint}/v1/chat/completions", json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        return ChatResponse(
            content=data["choices"][0]["message"]["content"],
            model=data.get("model", self.default_model),
            usage=data.get("usage"),
        )

    async def chat_stream(self, messages: List[Message], **kwargs) -> AsyncGenerator[ChatStreamChunk, None]:
        payload = {
            "model": kwargs.get("model", self.default_model),
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 2048),
            "stream": True,
        }
        headers = {"Authorization": f"Bearer {self.token}"}
        
        async with self.client.stream("POST", f"{self.endpoint}/v1/chat/completions", json=payload, headers=headers) as resp:
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