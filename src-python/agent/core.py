import json
import time
from typing import List, AsyncGenerator, Optional
from datetime import datetime

from src_python.llm.base import Message, ChatStreamChunk, ToolCall
from src_python.llm.manager import LLMManager, AllBackendsFailedError
from src_python.tools.base import ToolRegistry, ToolResult
from src_python.memory.session import SessionMemory
from src_python.agent.prompts import DEFAULT_SYSTEM_PROMPT
from src_python.config import Config


class Agent:
    def __init__(
        self,
        llm_manager: LLMManager,
        tool_registry: ToolRegistry,
        memory: SessionMemory,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT
    ):
        self.llm_manager = llm_manager
        self.tool_registry = tool_registry
        self.memory = memory
        self.system_prompt_template = system_prompt

    def _build_system_prompt(self) -> str:
        """Build the system prompt with current date and tool descriptions."""
        tool_descriptions = []
        for tool_spec in self.tool_registry.list_tools():
            params = tool_spec.parameters.get("properties", {})
            param_desc = ", ".join([f"{k}: {v.get('description', '')}" for k, v in params.items()])
            tool_descriptions.append(f"- {tool_spec.name}: {tool_spec.description} ({param_desc})")
        
        return self.system_prompt_template.format(
            date=datetime.now().strftime("%Y-%m-%d"),
            user_context="Desktop user with development background",
            tool_descriptions="\n".join(tool_descriptions)
        )

    def build_prompt(self, user_input: str, session_id: str) -> List[Message]:
        """Build the full prompt including system prompt, history, and user input."""
        messages = [
            Message(role="system", content=self._build_system_prompt())
        ]
        
        # Add conversation history (last 20 turns)
        history = self.memory.get_history(limit=20)
        messages.extend(history)
        
        # Add current user input
        messages.append(Message(role="user", content=user_input))
        
        return messages

    async def chat_stream(self, user_input: str, session_id: str) -> AsyncGenerator[ChatStreamChunk, None]:
        """Main chat loop with streaming, tool calling, and memory."""
        start_time = time.time()
        
        # Add user message to memory
        self.memory.add_turn("user", user_input)
        
        messages = self.build_prompt(user_input, session_id)
        tools = self.tool_registry.to_openai_functions()
        
        tool_calls_made = []
        tool_results = []
        backend_used = None
        full_response = ""
        
        try:
            # First LLM call
            async for chunk in self.llm_manager.chat_stream(messages, tools=tools):
                if chunk.tool_calls:
                    tool_calls_made.extend(chunk.tool_calls)
                if chunk.content:
                    full_response += chunk.content
                    yield chunk
                
                if chunk.done:
                    break
            
            # Execute tool calls if any
            if tool_calls_made:
                tool_results = await self._execute_tool_calls(tool_calls_made)
                
                # Add tool results to messages
                for tc, result in zip(tool_calls_made, tool_results):
                    messages.append(Message(
                        role="assistant",
                        content="",
                        tool_calls=[tc]
                    ))
                    messages.append(Message(
                        role="tool",
                        content=json.dumps(result.data) if result.success else f"Error: {result.error}",
                        tool_call_id=tc["id"]
                    ))
                
                # Second LLM call with tool results
                async for chunk in self.llm_manager.chat_stream(messages, tools=tools):
                    if chunk.content:
                        full_response += chunk.content
                        yield chunk
                    if chunk.done:
                        break
            
            # Add assistant response to memory
            latency_ms = int((time.time() - start_time) * 1000)
            self.memory.add_turn(
                "assistant",
                full_response,
                tool_calls=tool_calls_made,
                tool_results=[r.__dict__ if hasattr(r, '__dict__') else r for r in tool_results],
                latency_ms=latency_ms,
                backend_used=backend_used
            )
            
            # Final chunk
            yield ChatStreamChunk(content="", done=True, tool_calls=tool_calls_made)
            
        except AllBackendsFailedError as e:
            error_msg = f"I'm having trouble connecting to my language models: {e}"
            yield ChatStreamChunk(content=error_msg, done=True)
            self.memory.add_turn("assistant", error_msg, latency_ms=int((time.time() - start_time) * 1000))
        except Exception as e:
            error_msg = f"An error occurred: {e}"
            yield ChatStreamChunk(content=error_msg, done=True)
            self.memory.add_turn("assistant", error_msg, latency_ms=int((time.time() - start_time) * 1000))

    async def _execute_tool_calls(self, tool_calls: List[ToolCall]) -> List[ToolResult]:
        """Execute multiple tool calls in sequence."""
        results = []
        for tc in tool_calls:
            func = tc["function"]
            name = func["name"]
            try:
                args = json.loads(func["arguments"])
                result = self.tool_registry.execute(name, **args)
                results.append(result)
            except Exception as e:
                results.append(ToolResult(success=False, error=f"Failed to execute {name}: {e}"))
        return results