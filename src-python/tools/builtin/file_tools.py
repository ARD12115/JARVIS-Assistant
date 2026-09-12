import os
from pathlib import Path
from typing import Any
from src_python.tools.base import Tool, ToolResult


class FileReadTool(Tool):
    name = "file_read"
    description = "Read file contents with optional line range"
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path (relative to project root or absolute)"},
            "offset": {"type": "integer", "description": "Starting line (1-indexed)", "default": 1},
            "limit": {"type": "integer", "description": "Max lines to read", "default": 200}
        },
        "required": ["path"]
    }
    returns = {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "content": {"type": "string"},
            "lines_read": {"type": "integer"},
            "total_lines": {"type": "integer"}
        }
    }

    def execute(self, path: str, offset: int = 1, limit: int = 200) -> ToolResult:
        try:
            file_path = Path(path).expanduser().resolve()
            
            # Safety: restrict to project directory
            project_root = Path.cwd().resolve()
            try:
                file_path.relative_to(project_root)
            except ValueError:
                return ToolResult(success=False, error=f"Path outside project root: {path}")
            
            if not file_path.exists():
                return ToolResult(success=False, error=f"File not found: {path}")
            
            if not file_path.is_file():
                return ToolResult(success=False, error=f"Not a file: {path}")
            
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            total_lines = len(lines)
            start = max(0, offset - 1)
            end = min(start + limit, total_lines)
            selected_lines = lines[start:end]
            
            return ToolResult(success=True, data={
                "path": str(file_path),
                "content": "".join(selected_lines),
                "lines_read": len(selected_lines),
                "total_lines": total_lines
            })
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class FileWriteTool(Tool):
    name = "file_write"
    description = "Write content to file (creates directories if needed)"
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path"},
            "content": {"type": "string", "description": "Content to write"}
        },
        "required": ["path", "content"]
    }
    returns = {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "bytes_written": {"type": "integer"}
        }
    }

    def execute(self, path: str, content: str) -> ToolResult:
        try:
            file_path = Path(path).expanduser().resolve()
            
            # Safety: restrict to project directory
            project_root = Path.cwd().resolve()
            try:
                file_path.relative_to(project_root)
            except ValueError:
                return ToolResult(success=False, error=f"Path outside project root: {path}")
            
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, "w", encoding="utf-8") as f:
                bytes_written = f.write(content)
            
            return ToolResult(success=True, data={
                "path": str(file_path),
                "bytes_written": bytes_written
            })
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class FileListTool(Tool):
    name = "file_list"
    description = "List directory tree"
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Directory path", "default": "."},
            "depth": {"type": "integer", "description": "Max depth", "default": 3}
        },
        "required": []
    }
    returns = {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "tree": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "path": {"type": "string"},
                        "is_dir": {"type": "boolean"},
                        "size": {"type": "integer"}
                    }
                }
            }
        }
    }

    def execute(self, path: str = ".", depth: int = 3) -> ToolResult:
        try:
            dir_path = Path(path).expanduser().resolve()
            
            # Safety: restrict to project directory
            project_root = Path.cwd().resolve()
            try:
                dir_path.relative_to(project_root)
            except ValueError:
                return ToolResult(success=False, error=f"Path outside project root: {path}")
            
            if not dir_path.exists():
                return ToolResult(success=False, error=f"Directory not found: {path}")
            
            if not dir_path.is_dir():
                return ToolResult(success=False, error=f"Not a directory: {path}")
            
            tree = []
            for item in dir_path.rglob("*"):
                rel_depth = len(item.relative_to(dir_path).parts)
                if rel_depth > depth:
                    continue
                
                stat = item.stat()
                tree.append({
                    "name": item.name,
                    "path": str(item.relative_to(project_root)),
                    "is_dir": item.is_dir(),
                    "size": stat.st_size if item.is_file() else 0
                })
            
            # Sort: directories first, then files
            tree.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
            
            return ToolResult(success=True, data={
                "path": str(dir_path.relative_to(project_root)),
                "tree": tree
            })
        except Exception as e:
            return ToolResult(success=False, error=str(e))