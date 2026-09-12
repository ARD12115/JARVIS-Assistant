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
        # Try browser-use first (no API key needed)
        try:
            from browser_use import Browser, Agent as BrowserAgent
            from browser_use.llm import ChatOpenAI
            
            browser = Browser()
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
            await browser.close()
            
            if results:
                return ToolResult(success=True, data={"results": results})
        except Exception as e:
            print(f"browser-use search failed: {e}")
        
        # Fallback to Brave API if available
        if self.config.brave_key:
            return await self._brave_search(query, max_results)
        
        # Fallback to SerpAPI if available
        if self.config.serpapi_key:
            return await self._serpapi_search(query, max_results)
        
        return ToolResult(success=False, error="No search provider available (need browser-use, Brave, or SerpAPI)")

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