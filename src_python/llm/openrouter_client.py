import json
from typing import Dict, List, AsyncGenerator

import httpx

from src_python.llm.base import LLMBackend, Message, ChatResponse, ChatStreamChunk
from src_python.config import Config


class OpenRouterClient(LLMBackend):
    def __init__(self, config: Config):
        self.key = config.openrouter_key
        self.client = httpx.AsyncClient(
            base_url="https://openrouter.ai/api/v1",
            timeout=60.0,
            headers={"Authorization": f"Bearer {self.key}"} if self.key else {},
        )
        self.default_model = "meta-llama/llama-3.1-8b-instruct:free"

    def is_available(self) -> bool:
        return bool(self.key)

    def get_models(self) -> List[str]:
        return [self.default_model]

    def _build_payload(self, messages: List[Message], **kwargs) -> dict:
        payload = {
            "model": kwargs.get("model", self.default_model),
            "messages": [
                {
                    "role": message.role,
                    "content": message.content,
                    **({"tool_calls": message.tool_calls} if message.tool_calls else {}),
                    **({"tool_call_id": message.tool_call_id} if message.tool_call_id else {}),
                }
                for message in messages
            ],
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 2048),
            "stream": False,
        }
        if kwargs.get("tools"):
            payload["tools"] = kwargs["tools"]
        return payload

    def _parse_response(self, data: dict) -> ChatResponse:
        message = data["choices"][0]["message"]
        return ChatResponse(
            content=message.get("content") or "",
            model=data.get("model", self.default_model),
            usage=data.get("usage"),
            tool_calls=message.get("tool_calls"),
        )

    def chat(self, messages: List[Message], **kwargs) -> ChatResponse:
        payload = self._build_payload(messages, **kwargs)
        with httpx.Client(
            base_url="https://openrouter.ai/api/v1",
            timeout=60.0,
            headers={"Authorization": f"Bearer {self.key}"} if self.key else {},
        ) as client:
            resp = client.post("/chat/completions", json=payload)
        resp.raise_for_status()
        return self._parse_response(resp.json())

    async def _chat_async(self, messages: List[Message], **kwargs) -> ChatResponse:
        payload = self._build_payload(messages, **kwargs)
        resp = await self.client.post("/chat/completions", json=payload)
        resp.raise_for_status()
        return self._parse_response(resp.json())

    async def chat_stream(
        self, messages: List[Message], **kwargs
    ) -> AsyncGenerator[ChatStreamChunk, None]:
        payload = self._build_payload(messages, **kwargs)
        payload["stream"] = True
        tool_calls: Dict[str, Dict] = {}
        tool_call_indexes: Dict[int, str] = {}

        async with self.client.stream("POST", "/chat/completions", json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str.strip() == "[DONE]":
                    yield ChatStreamChunk(
                        content="",
                        done=True,
                        tool_calls=list(tool_calls.values()) or None,
                    )
                    break
                try:
                    data = json.loads(data_str)
                    choice = data["choices"][0]
                    delta = choice.get("delta", {})
                    for call in delta.get("tool_calls", []):
                        index = call.get("index", 0)
                        call_id = call.get("id")
                        key = call_id or tool_call_indexes.get(index) or str(index)
                        if call_id:
                            tool_call_indexes[index] = call_id
                        current = tool_calls.setdefault(
                            key,
                            {
                                "id": call_id or key,
                                "type": call.get("type", "function"),
                                "function": {"name": "", "arguments": ""},
                            },
                        )
                        function = call.get("function", {})
                        current["function"]["name"] += function.get("name", "")
                        current["function"]["arguments"] += function.get("arguments", "")

                    content = delta.get("content", "")
                    if content:
                        yield ChatStreamChunk(content=content, done=False)
                    if choice.get("finish_reason"):
                        yield ChatStreamChunk(
                            content="",
                            done=True,
                            tool_calls=list(tool_calls.values()) or None,
                        )
                        return
                except Exception:
                    continue
