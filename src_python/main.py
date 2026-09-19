import os
import json
import asyncio
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel

from src_python.config import Config
from src_python.llm.manager import LLMManager
from src_python.tools import create_tool_registry
from src_python.memory.session import SessionMemory
from src_python.agent.core import Agent
from src_python.voice.stt import stt_engine
from src_python.voice.tts import tts_engine
from src_python.llm.base import Message, ChatStreamChunk

MAX_AUDIO_UPLOAD_BYTES = 10 * 1024 * 1024

# Global instances
config = Config()
llm_manager = None
tool_registry = None
memory = None
agent = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global llm_manager, tool_registry, memory, agent
    
    # Initialize components
    llm_manager = LLMManager(config)
    tool_registry = create_tool_registry(config)
    memory = SessionMemory(config.db_path)
    agent = Agent(llm_manager, tool_registry, memory)
    
    print("JARVIS Backend initialized")
    print(f"Available backends: {list(llm_manager.get_status().keys())}")
    print(f"Available tools: {[t.name for t in tool_registry.list_tools()]}")
    
    yield
    
    # Cleanup
    print("Shutting down JARVIS Backend")


app = FastAPI(
    title="JARVIS Assistant API",
    version="0.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["tauri://localhost", "http://tauri.localhost", "https://tauri.localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response Models
class ChatRequest(BaseModel):
    session_id: str
    content: str
    stream: bool = True


class TTSRequest(BaseModel):
    text: str
    voice: Optional[str] = None


class MemoryLoadRequest(BaseModel):
    session_id: str


# Chat Endpoints
@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """Stream chat response with tool calling."""
    
    async def generate():
        try:
            async for chunk in agent.chat_stream(request.content, request.session_id):
                yield f"data: {chunk.model_dump_json()}\n\n"
        except Exception as e:
            yield f"data: {ChatStreamChunk(content=f'Error: {e}', done=True).model_dump_json()}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")


@app.post("/chat")
async def chat(request: ChatRequest):
    """Non-streaming chat response."""
    full_response = ""
    tool_calls = []
    
    async for chunk in agent.chat_stream(request.content, request.session_id):
        if chunk.content:
            full_response += chunk.content
        if chunk.tool_calls:
            tool_calls.extend(chunk.tool_calls)
        if chunk.done:
            break
    
    return {
        "content": full_response,
        "tool_calls": tool_calls
    }


# Voice Endpoints
@app.post("/voice/stt")
async def voice_stt(audio: UploadFile = File(...)):
    """Speech to text."""
    try:
        audio_bytes = await audio.read(MAX_AUDIO_UPLOAD_BYTES + 1)
        if len(audio_bytes) > MAX_AUDIO_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="Audio upload is too large")
        import io
        audio_file = io.BytesIO(audio_bytes)
        text = await stt_engine.transcribe(audio_file)
        return {"text": text}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/voice/tts")
async def voice_tts(request: TTSRequest):
    """Text to speech."""
    try:
        audio_bytes = await tts_engine.synthesize(request.text, request.voice)
        return Response(content=audio_bytes, media_type="audio/mpeg")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/voice/voices")
async def list_voices():
    """List available TTS voices."""
    return tts_engine.get_available_voices()


# Tool Endpoints
@app.get("/tools")
async def list_tools():
    """List available tools."""
    return [t.__dict__ for t in tool_registry.list_tools()]


@app.post("/tools/{tool_name}")
async def execute_tool(tool_name: str, params: dict):
    """Execute a specific tool."""
    try:
        result = await asyncio.to_thread(tool_registry.execute, tool_name, **params)
        return result.__dict__
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Tool not found: {tool_name}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Memory Endpoints
@app.get("/memory/sessions")
async def list_sessions():
    """List all conversation sessions."""
    sessions = memory.list_sessions()
    return [
        {
            "session_id": s.session_id,
            "started_at": s.started_at.isoformat(),
            "turn_count": s.turn_count,
            "preview": s.preview
        }
        for s in sessions
    ]


@app.get("/memory/history/{session_id}")
async def get_history(
    session_id: str,
    limit: int = Query(50, ge=1, le=SessionMemory.MAX_HISTORY_LIMIT),
):
    """Get conversation history for a session."""
    if not memory.session_exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    history = memory.get_history(limit=limit, session_id=session_id)
    
    return [
        {
            "role": m.role,
            "content": m.content,
            "tool_calls": m.tool_calls,
            "tool_call_id": m.tool_call_id
        }
        for m in history
    ]


@app.post("/memory/load")
async def load_session(request: MemoryLoadRequest):
    """Load/switch to a session."""
    success = memory.load_session(request.session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session_id": request.session_id, "loaded": True}


@app.post("/memory/new")
async def new_session():
    """Create a new session."""
    session_id = memory.new_session()
    return {"session_id": session_id}


# Health & Status
@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "backends": llm_manager.get_status(),
        "tools_count": len(tool_registry.list_tools())
    }


@app.get("/status")
async def status():
    """Detailed status."""
    return {
        "config": {
            "primary_backend": config.primary_backend,
            "fallback_backends": config.fallback_backends,
            "voice_enabled": config.voice_enabled
        },
        "backends": llm_manager.get_status(),
        "tools": [t.__dict__ for t in tool_registry.list_tools()],
        "current_session": memory.session_id
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src_python.main:app",
        host=config.api_host,
        port=config.api_port,
        reload=False
    )