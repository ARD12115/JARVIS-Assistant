import httpx
from typing import Any
from src_python.tools.base import Tool, ToolResult
from src_python.config import Config


class GetWeatherTool(Tool):
    name = "get_weather"
    description = "Get current weather for a location"
    parameters = {
        "type": "object",
        "properties": {
            "location": {"type": "string", "description": "City name or 'city,country' (e.g., 'Bangalore,IN')"}
        },
        "required": ["location"]
    }
    returns = {
        "type": "object",
        "properties": {
            "location": {"type": "string"},
            "temperature": {"type": "number"},
            "condition": {"type": "string"},
            "humidity": {"type": "number"},
            "wind_speed": {"type": "number"}
        }
    }

    def __init__(self, config: Config = None):
        self.config = config or Config()

    def execute(self, location: str) -> ToolResult:
        import asyncio
        return asyncio.run(self._execute_async(location))

    async def _execute_async(self, location: str) -> ToolResult:
        if not self.config.openweather_key:
            return ToolResult(success=False, error="OpenWeatherMap API key not configured")
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://api.openweathermap.org/data/2.5/weather",
                    params={
                        "q": location,
                        "appid": self.config.openweather_key,
                        "units": "metric"
                    }
                )
                resp.raise_for_status()
                data = resp.json()
            
            return ToolResult(success=True, data={
                "location": data["name"],
                "temperature": data["main"]["temp"],
                "condition": data["weather"][0]["description"],
                "humidity": data["main"]["humidity"],
                "wind_speed": data["wind"]["speed"]
            })
        except httpx.HTTPStatusError as e:
            return ToolResult(success=False, error=f"Weather API error: {e.response.status_code}")
        except Exception as e:
            return ToolResult(success=False, error=str(e))