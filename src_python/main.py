import os
import json
import asyncio
import time
from contextlib import asynccontextmanager
from typing import Optional
from collections import defaultdict

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Query, Request, Response, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field, field_validator
from starlette.middleware.base import BaseHTTPMiddleware

from src_python.config import Config
from src_python.llm.manager import LLMManager
from src_python.tools import create_tool_registry
from src_python.memory.session import SessionMemory
from src_python.agent.core import Agent
from src_python.voice.stt import stt_engine
from src_python.voice.tts import tts_engine
from src_python.llm.base import Message, ChatStreamChunk
from src_python.auth.session_auth import session_auth, SessionAuth

# Constants
MAX_AUDIO_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_JSON_BODY_SIZE = 1024 * 1024  # 1MB
MAX_SESSION_ID_LENGTH = 64
MAX_MESSAGE_LENGTH = 8192
RATE_LIMIT_REQUESTS = 60  # per minute
RATE_LIMIT_WINDOW = 60  # seconds

# Rate limiting storage (in production use Redis)
rate_limit_store: dict[str, list[float]] = defaultdict(list)

# Auth dependency
async def get_current_session(request: Request) -> str:
    """Extract and verify session token from Authorization header."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    
    token = auth_header[7:]  # Remove "Bearer "
    session_id = session_auth.verify_token(token, request)
    
    if not session_id:
        raise HTTPException(status_code=401, detail="Invalid or expired session token")
    
    return session_id


# Global instances
config = Config()
llm_manager = None
tool_registry = None
memory = None
agent = None


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "microphone=(), camera=(), geolocation=()"
        # Remove server header
        if "server" in response.headers:
            del response.headers["server"]
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiting."""
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/status"]:
            return await call_next(request)
        
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        
        # Clean old entries
        rate_limit_store[client_ip] = [
            ts for ts in rate_limit_store[client_ip] 
            if now - ts < RATE_LIMIT_WINDOW
        ]
        
        if len(rate_limit_store[client_ip]) >= RATE_LIMIT_REQUESTS:
            return JSONResponse(
                status_code=429,
                content={"error": "Rate limit exceeded. Try again later."},
                headers={"Retry-After": str(RATE_LIMIT_WINDOW)}
            )
        
        rate_limit_store[client_ip].append(now)
        return await call_next(request)


class RequestSizeMiddleware(BaseHTTPMiddleware):
    """Limit request body size."""
    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > MAX_JSON_BODY_SIZE:
            return JSONResponse(
                status_code=413,
                content={"error": "Request body too large"}
            )
        return await call_next(request)


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
    lifespan=lifespan,
    docs_url=None,  # Disable docs in production
    redoc_url=None,
)

# Security middleware (order matters - outermost first)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestSizeMiddleware)
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=["localhost", "127.0.0.1", "tauri.localhost"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["tauri://localhost", "http://tauri.localhost", "https://tauri.localhost"],
    allow_credentials=True,
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type", "Authorization"],
    max_age=3600,
)


# Request/Response Models with validation
class ChatRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=MAX_SESSION_ID_LENGTH, pattern=r"^[a-zA-Z0-9_-]+$")
    content: str = Field(..., min_length=1, max_length=MAX_MESSAGE_LENGTH)
    stream: bool = True

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, v: str) -> str:
        # Only allow alphanumeric, underscore, hyphen
        import re
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("Invalid session_id format")
        return v

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        # Basic sanitization
        if any(ord(c) < 32 and c not in '\n\r\t' for c in v):
            raise ValueError("Invalid characters in content")
        return v


class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    voice: Optional[str] = Field(None, max_length=50)

    @field_validator("voice")
    @classmethod
    def validate_voice(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            # Only allow known voice names
            allowed = {
                "aria", "guy", "jenny", "davis", "jane", 
                "jason", "sara", "tony", "nancy",
                "en-US-AriaNeural", "en-US-GuyNeural", "en-US-JennyNeural",
                "en-US-DavisNeural", "en-US-JaneNeural", "en-US-JasonNeural",
                "en-US-SaraNeural", "en-US-TonyNeural", "en-US-NancyNeural"
            }
            if v not in allowed:
                raise ValueError("Invalid voice")
        return v


class MemoryLoadRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=MAX_SESSION_ID_LENGTH, pattern=r"^[a-zA-Z0-9_-]+$")


class ToolExecuteRequest(BaseModel):
    tool_name: str = Field(..., min_length=1, max_length=50, pattern=r"^[a-z_]+$")
    params: dict = Field(default_factory=dict)


# Chat Endpoints
@app.post("/chat/stream")
async def chat_stream(request: ChatRequest, session_id: str = Depends(get_current_session)):
    """Stream chat response with tool calling."""
    # Verify session_id matches authenticated session
    if request.session_id != session_id:
        raise HTTPException(status_code=403, detail="Session ID mismatch")
    
    async def generate():
        try:
            async for chunk in agent.chat_stream(request.content, session_id):
                yield f"data: {chunk.model_dump_json()}\n\n"
        except Exception as e:
            # Sanitized error - no internal details
            yield f"data: {ChatStreamChunk(content='An error occurred processing your request', done=True).model_dump_json()}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")


@app.post("/chat")
async def chat(request: ChatRequest, session_id: str = Depends(get_current_session)):
    """Non-streaming chat response."""
    # Verify session_id matches authenticated session
    if request.session_id != session_id:
        raise HTTPException(status_code=403, detail="Session ID mismatch")
    
    full_response = ""
    tool_calls = []
    
    try:
        async for chunk in agent.chat_stream(request.content, session_id):
            if chunk.content:
                full_response += chunk.content
            if chunk.tool_calls:
                tool_calls.extend(chunk.tool_calls)
            if chunk.done:
                break
    except Exception:
        # Sanitized error
        full_response = "An error occurred processing your request"
    
    return {
        "content": full_response,
        "tool_calls": tool_calls
    }


# Voice Endpoints
@app.post("/voice/stt")
async def voice_stt(audio: UploadFile = File(...), session_id: str = Depends(get_current_session)):
    """Speech to text."""
    try:
        # Validate content type
        if audio.content_type not in ["audio/webm", "audio/wav", "audio/ogg", "audio/mpeg"]:
            raise HTTPException(status_code=400, detail="Invalid audio format")
        
        audio_bytes = await audio.read(MAX_AUDIO_UPLOAD_BYTES + 1)
        if len(audio_bytes) > MAX_AUDIO_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="Audio upload too large (max 10MB)")
        
        import io
        audio_file = io.BytesIO(audio_bytes)
        text = await stt_engine.transcribe(audio_file)
        return {"text": text}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to process audio")


@app.post("/voice/tts")
async def voice_tts(request: TTSRequest, session_id: str = Depends(get_current_session)):
    """Text to speech."""
    try:
        audio_bytes = await tts_engine.synthesize(request.text, request.voice)
        return Response(content=audio_bytes, media_type="audio/mpeg")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to synthesize speech")


@app.get("/voice/voices")
async def list_voices(session_id: str = Depends(get_current_session)):
    """List available TTS voices."""
    return tts_engine.get_available_voices()


# Tool Endpoints
@app.get("/tools")
async def list_tools(session_id: str = Depends(get_current_session)):
    """List available tools."""
    return [{"name": t.name, "description": t.description, "parameters": t.parameters, "returns": t.returns} for t in tool_registry.list_tools()]


@app.post("/tools/{tool_name}")
async def execute_tool(tool_name: str, params: dict, session_id: str = Depends(get_current_session)):
    """Execute a specific tool."""
    # Validate tool name
    if not tool_name or not tool_name.replace("_", "").isalnum():
        raise HTTPException(status_code=400, detail="Invalid tool name")
    
    try:
        result = await asyncio.to_thread(tool_registry.execute, tool_name, **params)
        return {"success": result.success, "data": result.data, "error": result.error}
    except KeyError:
        raise HTTPException(status_code=404, detail="Tool not found")
    except Exception:
        raise HTTPException(status_code=500, detail="Tool execution failed")


# Memory Endpoints
@app.get("/memory/sessions")
async def list_sessions(auth_session_id: str = Depends(get_current_session)):
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
    auth_session_id: str = Depends(get_current_session),
):
    """Get conversation history for a session."""
    if session_id != auth_session_id:
        raise HTTPException(status_code=403, detail="Session ID mismatch")
    
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
async def load_session(request: MemoryLoadRequest, auth_session_id: str = Depends(get_current_session)):
    """Load/switch to a session."""
    if request.session_id != auth_session_id:
        raise HTTPException(status_code=403, detail="Session ID mismatch")
    
    success = memory.load_session(request.session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session_id": request.session_id, "loaded": True}


@app.post("/memory/new")
async def new_session(request: Request):
    """Create a new session and return auth token."""
    session_id = memory.new_session()
    
    # Generate auth token for the new session
    token = session_auth.create_token(session_id, request)
    
    return {
        "session_id": session_id,
        "token": token,
        "expires_in": session_auth.token_ttl
    }


# Health & Status (no rate limiting)
@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "backends": {
            name: {"healthy": True, "models": info["models"]} 
            for name, info in llm_manager.get_status().items()
        },
        "tools_count": len(tool_registry.list_tools())
    }


@app.get("/status")
async def status():
    """Detailed status."""
    backend_status = await asyncio.to_thread(lambda: llm_manager.get_status())
    return {
        "config": {
            "primary_backend": config.primary_backend,
            "fallback_backends": config.fallback_backends,
            "voice_enabled": config.voice_enabled
        },
        "backends": backend_status,
        "tools": [{"name": t.name, "description": t.description} for t in tool_registry.list_tools()],
        "current_session": memory.session_id
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src_python.main:app",
        host=config.api_host,
        port=config.api_port,
        reload=False,
        access_log=False,  # Disable access logs in production
    )