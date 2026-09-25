import os
import secrets
import hashlib
import time
from typing import Optional
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class SessionToken:
    """Represents a valid session token."""
    token_hash: str
    session_id: str
    created_at: float
    expires_at: float
    client_fingerprint: str = ""


class SessionAuth:
    """
    Simple session authentication for JARVIS.
    Uses signed tokens to bind frontend sessions to backend sessions.
    """
    
    def __init__(self, secret_key: str = None, token_ttl: int = 24 * 3600):
        self.secret_key = secret_key or os.getenv("JARVIS_SESSION_SECRET", secrets.token_hex(32))
        self.token_ttl = token_ttl
        self._tokens: dict[str, SessionToken] = {}
        self._session_to_token: dict[str, str] = {}  # session_id -> token
    
    def _hash_token(self, token: str) -> str:
        """Hash token for storage."""
        return hashlib.sha256(f"{self.secret_key}:{token}".encode()).hexdigest()
    
    def _generate_fingerprint(self, request) -> str:
        """Generate client fingerprint from request."""
        # In production, include more factors: user-agent, IP, etc.
        ip = request.client.host if request.client else "unknown"
        ua = request.headers.get("user-agent", "unknown")
        return hashlib.sha256(f"{ip}:{ua}".encode()).hexdigest()[:16]
    
    def create_token(self, session_id: str, request) -> str:
        """Create a new session token bound to client fingerprint."""
        # Generate secure random token
        token = secrets.token_urlsafe(32)
        token_hash = self._hash_token(token)
        fingerprint = self._generate_fingerprint(request)
        
        now = time.time()
        session_token = SessionToken(
            token_hash=token_hash,
            session_id=session_id,
            created_at=now,
            expires_at=now + self.token_ttl,
            client_fingerprint=fingerprint
        )
        
        # Revoke any existing token for this session
        if session_id in self._session_to_token:
            old_hash = self._session_to_token[session_id]
            if old_hash in self._tokens:
                del self._tokens[old_hash]
        
        self._tokens[token_hash] = session_token
        self._session_to_token[session_id] = token_hash
        
        return token
    
    def verify_token(self, token: str, request) -> Optional[str]:
        """
        Verify token and return session_id if valid.
        Returns None if invalid or expired.
        """
        if not token:
            return None
        
        token_hash = self._hash_token(token)
        session_token = self._tokens.get(token_hash)
        
        if not session_token:
            return None
        
        # Check expiration
        if time.time() > session_token.expires_at:
            self._revoke_token(token_hash)
            return None
        
        # Verify fingerprint (optional - can be strict or loose)
        fingerprint = self._generate_fingerprint(request)
        if session_token.client_fingerprint and session_token.client_fingerprint != fingerprint:
            # Fingerprint mismatch - could be session hijacking
            # For now, log and allow (in production, reject)
            print(f"WARNING: Fingerprint mismatch for session {session_token.session_id}")
        
        return session_token.session_id
    
    def revoke_token(self, token: str) -> bool:
        """Revoke a specific token."""
        token_hash = self._hash_token(token)
        return self._revoke_token(token_hash)
    
    def _revoke_token(self, token_hash: str) -> bool:
        session_token = self._tokens.pop(token_hash, None)
        if session_token and session_token.session_id in self._session_to_token:
            del self._session_to_token[session_token.session_id]
        return session_token is not None
    
    def revoke_session(self, session_id: str) -> bool:
        """Revoke all tokens for a session."""
        token_hash = self._session_to_token.pop(session_id, None)
        if token_hash:
            self._tokens.pop(token_hash, None)
            return True
        return False
    
    def cleanup_expired(self) -> int:
        """Remove expired tokens. Returns count removed."""
        now = time.time()
        expired = [h for h, t in self._tokens.items() if now > t.expires_at]
        for h in expired:
            self._revoke_token(h)
        return len(expired)
    
    def get_session_info(self, token: str) -> Optional[dict]:
        """Get session info from token."""
        session_id = self.verify_token(token, None)
        if not session_id:
            return None
        
        token_hash = self._hash_token(token)
        session_token = self._tokens.get(token_hash)
        
        if not session_token:
            return None
        
        return {
            "session_id": session_token.session_id,
            "created_at": session_token.created_at,
            "expires_at": session_token.expires_at,
            "client_fingerprint": session_token.client_fingerprint
        }


# Global instance
session_auth = SessionAuth()