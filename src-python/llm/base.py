from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncGenerator
from dataclasses import dataclass


@dataclass
class Message:
    role: str
    content: str
    tool_calls: List[Dict[str, Any]] = None
    tool_call_id: str = None


@dataclass
class ChatResponse:
    content: str
    model: str
    usage: Optional[Dict[str, int]] = None
    latency_ms: int = None


@dataclass
class ChatStreamChunk:
    content: str
    done: bool
    tool_calls: List[Dict[str, Any]] = None


@dataclass
class ToolCall:
    id: str
    type: str
    function: Dict[str, Any]


class LLMBackend(ABC):
    @abstractmethod
    def chat(self, messages: List[Message], **kwargs) -> ChatResponse:
        pass

    @abstractmethod
    async def chat_stream(self, messages: List[Message], **kwargs) -> AsyncGenerator[ChatStreamChunk, None]:
        pass

    @abstractmethod
    def is_available(self) -> bool:
        pass

    @abstractmethod
    def get_models(self) -> List[str]:
        pass