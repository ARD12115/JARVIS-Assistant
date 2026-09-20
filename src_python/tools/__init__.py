from src_python.tools.builtin.time_tool import GetTimeTool
from src_python.tools.builtin.weather_tool import GetWeatherTool
from src_python.tools.builtin.web_search_tool import WebSearchTool
from src_python.tools.builtin.system_info_tool import SystemInfoTool
from src_python.tools.builtin.file_tools import FileReadTool, FileWriteTool, FileListTool
from src_python.tools.builtin.code_exec_tool import CodeExecTool
from src_python.tools.base import ToolRegistry
from src_python.config import Config


def create_tool_registry(config: Config = None) -> ToolRegistry:
    """Create and populate the tool registry with all built-in tools."""
    registry = ToolRegistry()
    cfg = config or Config()
    
    # Register tools (some need config)
    registry.register(GetTimeTool())
    registry.register(GetWeatherTool(cfg))
    registry.register(WebSearchTool(cfg))
    registry.register(SystemInfoTool())
    registry.register(FileReadTool())
    registry.register(FileWriteTool())
    registry.register(FileListTool())
    
    # Conditionally register code execution tool (security-sensitive)
    if cfg.code_exec_enabled:
        registry.register(CodeExecTool())
    
    return registry


__all__ = [
    "GetTimeTool",
    "GetWeatherTool", 
    "WebSearchTool",
    "SystemInfoTool",
    "FileReadTool",
    "FileWriteTool",
    "FileListTool",
    "CodeExecTool",
    "create_tool_registry",
]