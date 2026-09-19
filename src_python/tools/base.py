from abc import ABC, abstractmethod
from typing import Any, Dict
from dataclasses import dataclass


@dataclass
class ToolResult:
    success: bool
    data: Any = None
    error: str = None


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: Dict  # JSON Schema
    returns: Dict     # JSON Schema


class Tool(ABC):
    name: str
    description: str
    parameters: Dict  # JSON Schema
    returns: Dict     # JSON Schema

    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        pass


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        if name not in self._tools:
            raise KeyError(f"Tool not found: {name}")
        return self._tools[name]

    def list_tools(self) -> list[ToolSpec]:
        return [
            ToolSpec(
                name=tool.name,
                description=tool.description,
                parameters=tool.parameters,
                returns=tool.returns
            )
            for tool in self._tools.values()
        ]

    def execute(self, name: str, **kwargs) -> ToolResult:
        tool = self.get(name)
        try:
            return tool.execute(**kwargs)
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def to_openai_functions(self) -> list[Dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters
                }
            }
            for tool in self._tools.values()
        ]