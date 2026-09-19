import json
import httpx
from typing import Dict, List, AsyncGenerator

from src_python.llm.base import LLMBackend, Message, ChatResponse, ChatStreamChunk
from src_python.config import Config


class NVIDIANIMClient(LLMBackend):
    def __init__(self, config: Config):
        self.key = config.nvidia_nim_api_key
        self.base_url = config.nvidia_nim_base_url or "https://integrate.api.nvidia.com/v1"
        # Use the working model from config
        self.model = config.nvidia_nim_model or "nvidia/nemotron-3-super-120b-a12b"
        # Use sync client for sync methods
        self.sync_client = httpx.Client(
            base_url=self.base_url,
            timeout=60.0,
            headers={"Authorization": f"Bearer {self.key}"} if self.key else {},
        )
        # Use async client for streaming
        self.async_client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=60.0,
            headers={"Authorization": f"Bearer {self.key}"} if self.key else {},
        )

    def is_available(self) -> bool:
        # Actually test the API with a simple request
        if not self.key:
            return False
        try:
            # Quick sync check
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"},
                    json={"model": self.model, "messages": [{"role": "user", "content": "test"}], "max_tokens": 1},
                )
                return resp.status_code == 200
        except Exception:
            return False

    def get_models(self) -> List[str]:
        return [self.model]

    def _build_payload(self, messages: List[Message], **kwargs) -> dict:
        payload = {
            "model": kwargs.get("model", self.model),
            "messages": [
                {
                    "role": message.role,
                    "content": message.content,
                    **(({"tool_calls": message.tool_calls} if message.tool_calls else {})),
                    **(({"tool_call_id": message.tool_call_id} if message.tool_call_id else {})),
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
            content=message.get("content", ""),
            model=self.model,
            usage=data.get("usage", {}),
            tool_calls=message.get("tool_calls"),
        )

    def chat(self, messages: List[Message], **kwargs) -> ChatResponse:
        payload = self._build_payload(messages, **kwargs)
        response = self.sync_client.post("/chat/completions", json=payload)
        response.raise_for_status()
        return self._parse_response(response.json())

    async def chat_stream(self, messages: List[Message], **kwargs) -> AsyncGenerator[ChatStreamChunk, None]:
        payload = self._build_payload(messages, **kwargs)
        payload["stream"] = True
        
        # Make the streaming request
        req = self.async_client.build_request("POST", "/chat/completions", json=payload)
        response = await self.async_client.send(req, stream=True)
        
        # Check status
        if response.status_code != 200:
            yield ChatStreamChunk(content="", tool_calls=None, done=True)
            return
        
        # Process stream
        try:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        chunk_data = json.loads(data)
                        delta = chunk_data["choices"][0].get("delta", {})
                        content = delta.get("content", "")
                        if content or delta.get("tool_calls"):
                            yield ChatStreamChunk(
                                content=content,
                                tool_calls=delta.get("tool_calls"),
                                done=False,
                            )
                    except Exception:
                        pass
        finally:
            await response.aclose()
        
        yield ChatStreamChunk(content="", tool_calls=None, done=True)