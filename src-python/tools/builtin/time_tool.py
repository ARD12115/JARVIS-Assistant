from datetime import datetime
from typing import Any
import zoneinfo
from src_python.tools.base import Tool, ToolResult


class GetTimeTool(Tool):
    name = "get_time"
    description = "Get current time in specified timezone"
    parameters = {
        "type": "object",
        "properties": {
            "timezone": {"type": "string", "description": "IANA timezone (e.g., 'Asia/Kolkata', 'America/New_York', 'UTC')"}
        },
        "required": []
    }
    returns = {
        "type": "object",
        "properties": {
            "time": {"type": "string"},
            "timezone": {"type": "string"},
            "iso": {"type": "string"}
        }
    }

    def execute(self, timezone: str = "UTC") -> ToolResult:
        try:
            tz = zoneinfo.ZoneInfo(timezone)
        except Exception:
            return ToolResult(success=False, error=f"Invalid timezone: {timezone}")
        
        now = datetime.now(tz)
        return ToolResult(success=True, data={
            "time": now.strftime("%Y-%m-%d %H:%M:%S %Z"),
            "timezone": str(tz),
            "iso": now.isoformat()
        })