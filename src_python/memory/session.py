import sqlite3
import json
import uuid
from typing import Any, List, Optional
from datetime import datetime
from pathlib import Path

from src_python.llm.base import Message, ToolCall
from src_python.memory.models import SessionSummary
from src_python.config import Config


class SessionMemory:
    MAX_HISTORY_LIMIT = 1000

    def __init__(self, db_path: str = None, session_id: str = None):
        self.db_path = db_path or Config().db_path
        self.session_id = session_id or str(uuid.uuid4())
        self._init_db()

    def _init_db(self):
        """Initialize database schema with WAL mode for better concurrency."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    turn_index INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tool_calls TEXT,
                    tool_results TEXT,
                    latency_ms INTEGER,
                    backend_used TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_session_turn 
                ON conversations(session_id, turn_index)
            """)
            conn.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS uq_session_turn
                ON conversations(session_id, turn_index)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_session_created 
                ON conversations(created_at)
            """)
            conn.commit()

    def add_turn(
        self,
        role: str,
        content: str,
        tool_calls: Optional[List[ToolCall]] = None,
        tool_results: Optional[List[Any]] = None,
        latency_ms: Optional[int] = None,
        backend_used: Optional[str] = None,
        session_id: str = None,
    ) -> int:
        """Add a conversation turn. Returns the turn index."""
        session_id = session_id or self.session_id
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            turn_index = conn.execute(
                "SELECT COALESCE(MAX(turn_index), -1) + 1 "
                "FROM conversations WHERE session_id = ?",
                (session_id,),
            ).fetchone()[0]
            conn.execute("""
                INSERT INTO conversations 
                (session_id, turn_index, role, content, tool_calls, tool_results, latency_ms, backend_used)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                turn_index,
                role,
                content,
                json.dumps([tc.__dict__ if hasattr(tc, '__dict__') else tc for tc in (tool_calls or [])]),
                json.dumps(tool_results or []),
                latency_ms,
                backend_used
            ))
            conn.commit()
        
        return turn_index

    def get_history(self, limit: int = 50, session_id: str = None) -> List[Message]:
        """Get recent conversation history for this session."""
        if not 1 <= limit <= self.MAX_HISTORY_LIMIT:
            raise ValueError(
                f"History limit must be between 1 and {self.MAX_HISTORY_LIMIT}"
            )
        session_id = session_id or self.session_id
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT role, content, tool_calls
                FROM conversations
                WHERE session_id = ? AND turn_index >= 0
                ORDER BY turn_index DESC
                LIMIT ?
            """, (session_id, limit))
            rows = cursor.fetchall()
        
        # Reverse to get chronological order
        messages = []
        for row in reversed(rows):
            tool_calls = json.loads(row["tool_calls"]) if row["tool_calls"] else None
            messages.append(Message(
                role=row["role"],
                content=row["content"],
                tool_calls=tool_calls,
                tool_call_id=None
            ))
        
        return messages

    def search(self, query: str, limit: int = 10) -> List[Message]:
        """Search conversation history by content."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT role, content, tool_calls
                FROM conversations
                WHERE session_id = ? AND content LIKE ?
                ORDER BY turn_index DESC
                LIMIT ?
            """, (self.session_id, f"%{query}%", limit))
            rows = cursor.fetchall()
        
        messages = []
        for row in reversed(rows):
            tool_calls = json.loads(row["tool_calls"]) if row["tool_calls"] else None
            messages.append(Message(
                role=row["role"],
                content=row["content"],
                tool_calls=tool_calls,
                tool_call_id=None
            ))
        
        return messages

    def summarize(self, max_turns: int = 100) -> str:
        """Generate a summary of the conversation."""
        messages = self.get_history(limit=max_turns)
        if not messages:
            return "No conversation history."
        
        # Simple summary: count by role, list topics
        user_count = sum(1 for m in messages if m.role == "user")
        assistant_count = sum(1 for m in messages if m.role == "assistant")
        tool_count = sum(1 for m in messages if m.role == "tool")
        
        # Extract key topics from user messages
        user_messages = [m.content for m in messages if m.role == "user"]
        topics = user_messages[:5]  # First 5 user messages as topics
        
        return f"""Session Summary:
- Total turns: {len(messages)}
- User messages: {user_count}
- Assistant responses: {assistant_count}
- Tool calls: {tool_count}
- Recent topics: {topics}"""

    def get_session_id(self) -> str:
        return self.session_id

    def new_session(self) -> str:
        """Create a new session and insert a placeholder record."""
        self.session_id = str(uuid.uuid4())
        # Insert a placeholder system message so the session appears in the list immediately
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("""
                INSERT INTO conversations 
                (session_id, turn_index, role, content, tool_calls, tool_results, latency_ms, backend_used)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                self.session_id,
                -1,  # Special index for session placeholder
                "system",
                "Session created",
                "[]",
                "[]",
                None,
                None
            ))
            conn.commit()
        return self.session_id

    def list_sessions(self) -> List[SessionSummary]:
        """List all sessions with summary info."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT 
                    c.session_id,
                    MIN(created_at) as started_at,
                    COUNT(*) as turn_count,
                    (
                        SELECT content
                        FROM conversations AS latest
                        WHERE latest.session_id = c.session_id
                          AND latest.role = 'user'
                          AND latest.turn_index >= 0
                        ORDER BY latest.turn_index DESC
                        LIMIT 1
                    ) as last_user_msg
                FROM conversations AS c
                WHERE c.turn_index >= 0
                GROUP BY c.session_id
                ORDER BY started_at DESC
            """)
            rows = cursor.fetchall()
        
        sessions = []
        for row in rows:
            preview = row["last_user_msg"] or ""
            if len(preview) > 80:
                preview = preview[:77] + "..."
            sessions.append(SessionSummary(
                session_id=row["session_id"],
                started_at=datetime.fromisoformat(row["started_at"]),
                turn_count=row["turn_count"],
                preview=preview
            ))
        
        return sessions

    def session_exists(self, session_id: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute(
                "SELECT 1 FROM conversations WHERE session_id = ? LIMIT 1",
                (session_id,),
            ).fetchone() is not None

    def load_session(self, session_id: str) -> bool:
        """Switch to an existing session."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT 1 FROM conversations WHERE session_id = ? LIMIT 1",
                (session_id,)
            )
            if cursor.fetchone():
                self.session_id = session_id
                return True
        return False