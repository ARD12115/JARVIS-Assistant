import asyncio
from typing import Any
from src_python.tools.base import Tool, ToolResult
from src_python.config import Config


class WebSearchTool(Tool):
    name = "web_search"
    description = "Search the web and return snippets"
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "max_results": {"type": "integer", "description": "Maximum results to return", "default": 5}
        },
        "required": ["query"]
    }
    returns = {
        "type": "object",
        "properties": {
            "results": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "url": {"type": "string"},
                        "snippet": {"type": "string"}
                    }
                }
            }
        }
    }

    def __init__(self, config: Config = None):
        self.config = config or Config()

    def execute(self, query: str, max_results: int = 5) -> ToolResult:
        return asyncio.run(self._execute_async(query, max_results))

    async def _execute_async(self, query: str, max_results: int = 5) -> ToolResult:
        # Prefer a configured search API first — it's an order of magnitude
        # cheaper and faster than spinning up a full headless browser.
        if self.config.brave_key:
            result = await self._brave_search(query, max_results)
            if result.success:
                return result
        if self.config.serpapi_key:
            result = await self._serpapi_search(query, max_results)
            if result.success:
                return result

        # Fall back to browser-use (no API key needed, but a cold browser
        # launch per search is heavy — only worth it when nothing else works)
        try:
            from browser_use import Browser
            
            browser = Browser()
            try:
                await browser.start()
                # Use a simple search approach without full agent for speed
                page = await browser.new_page()
                await page.goto(f"https://duckduckgo.com/html/?q={query.replace(' ', '+')}")
                
                results = await page.evaluate(f"""
                    () => {{
                        const items = document.querySelectorAll('.result__snippet');
                        return Array.from(items).slice(0, {max_results}).map(el => ({{
                            title: el.closest('.result')?.querySelector('.result__title')?.textContent || '',
                            url: el.closest('.result')?.querySelector('.result__url')?.textContent || '',
                            snippet: el.textContent || ''
                        }}));
                    }}
                """)
            finally:
                await browser.stop()
            
            if results:
                return ToolResult(success=True, data={"results": results})
        except Exception as e:
            print(f"browser-use search failed: {e}")

        return ToolResult(success=False, error="No search provider available (need Brave, SerpAPI, or browser-use)")

    async def _brave_search(self, query: str, max_results: int) -> ToolResult:
        import httpx
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://api.search.brave.com/res/v1/web/search",
                    headers={"Accept": "application/json", "X-Subscription-Token": self.config.brave_key},
                    params={"q": query, "count": max_results}
                )
                resp.raise_for_status()
                data = resp.json()
                results = [
                    {
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "snippet": item.get("description", "")
                    }
                    for item in data.get("web", {}).get("results", [])
                ]
                return ToolResult(success=True, data={"results": results})
        except Exception as e:
            return ToolResult(success=False, error=f"Brave search failed: {e}")

    async def _serpapi_search(self, query: str, max_results: int) -> ToolResult:
        import httpx
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://serpapi.com/search",
                    params={"q": query, "api_key": self.config.serpapi_key, "num": max_results, "engine": "google"}
                )
                resp.raise_for_status()
                data = resp.json()
                results = [
                    {
                        "title": item.get("title", ""),
                        "url": item.get("link", ""),
                        "snippet": item.get("snippet", "")
                    }
                    for item in data.get("organic_results", [])
                ]
                return ToolResult(success=True, data={"results": results})
        except Exception as e:
            return ToolResult(success=False, error=f"SerpAPI search failed: {e}")