from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class SessionSummary:
    session_id: str
    started_at: datetime
    turn_count: int
    preview: str