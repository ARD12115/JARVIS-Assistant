import os
from pathlib import Path
from typing import Any
from src_python.tools.base import Tool, ToolResult


def _resolve_safe_path(path: str, project_root: Path) -> tuple[Path | None, str | None]:
    """
    Safely resolve a path within project root.
    Returns (resolved_path, error_message).
    """
    try:
        # Convert to Path and expand user
        file_path = Path(path).expanduser()
        
        # Get absolute path without resolving symlinks first
        abs_path = file_path.resolve(strict=False)
        
        # Check if the resolved path is within project root
        # We need to check each parent to prevent symlink traversal
        try:
            # This will fail if abs_path is not under project_root
            abs_path.relative_to(project_root)
        except ValueError:
            return None, f"Path outside project root: {path}"
        
        # Additional safety: check if any parent is a symlink pointing outside
        current = abs_path
        while current != project_root and current != current.parent:
            if current.is_symlink():
                # Get the real target of the symlink
                try:
                    real_target = current.resolve(strict=True)
                    real_target.relative_to(project_root)
                except (ValueError, OSError):
                    return None, f"Symlink points outside project root: {current}"
            current = current.parent
        
        return abs_path, None
    except Exception as e:
        return None, f"Invalid path: {path} ({e})"


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
            project_root = Path.cwd().resolve()
            safe_path, error = _resolve_safe_path(path, project_root)
            
            if error:
                return ToolResult(success=False, error=error)
            
            if not safe_path.exists():
                return ToolResult(success=False, error=f"File not found: {path}")
            
            if not safe_path.is_file():
                return ToolResult(success=False, error=f"Not a file: {path}")
            
            # Prevent reading extremely large files
            stat = safe_path.stat()
            if stat.st_size > 10 * 1024 * 1024:  # 10MB limit
                return ToolResult(success=False, error=f"File too large: {stat.st_size} bytes (max 10MB)")
            
            with open(safe_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            total_lines = len(lines)
            start = max(0, offset - 1)
            end = min(start + limit, total_lines)
            selected_lines = lines[start:end]
            
            return ToolResult(success=True, data={
                "path": str(safe_path.relative_to(project_root)),
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
            # Size limit on content
            if len(content.encode('utf-8')) > 10 * 1024 * 1024:  # 10MB
                return ToolResult(success=False, error="Content too large (max 10MB)")
            
            project_root = Path.cwd().resolve()
            safe_path, error = _resolve_safe_path(path, project_root)
            
            if error:
                return ToolResult(success=False, error=error)
            
            # Prevent overwriting sensitive files
            sensitive_patterns = [
                ".env", ".env.*", "*.key", "*.pem", "*.crt", "*.p12", "*.pfx",
                "id_rsa", "id_ed25519", "authorized_keys", "known_hosts",
                "config.json", "secrets.*", "credentials.*"
            ]
            
            rel_path = safe_path.relative_to(project_root)
            for pattern in sensitive_patterns:
                import fnmatch
                if fnmatch.fnmatch(rel_path.name.lower(), pattern.lower()):
                    return ToolResult(success=False, error=f"Writing to sensitive file blocked: {rel_path}")
            
            # Create parent directories
            safe_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write atomically using temp file + rename
            import tempfile
            with tempfile.NamedTemporaryFile(
                mode="w", 
                encoding="utf-8", 
                dir=safe_path.parent, 
                delete=False,
                prefix=f".{safe_path.name}.tmp.",
                suffix=".tmp"
            ) as tf:
                tf.write(content)
                temp_path = tf.name
            
            try:
                os.replace(temp_path, safe_path)  # Atomic on POSIX, best-effort on Windows
            except Exception:
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass
                raise
            
            return ToolResult(success=True, data={
                "path": str(rel_path),
                "bytes_written": len(content.encode('utf-8'))
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
            project_root = Path.cwd().resolve()
            safe_path, error = _resolve_safe_path(path, project_root)
            
            if error:
                return ToolResult(success=False, error=error)
            
            if not safe_path.exists():
                return ToolResult(success=False, error=f"Directory not found: {path}")
            
            if not safe_path.is_dir():
                return ToolResult(success=False, error=f"Not a directory: {path}")
            
            # Limit depth
            if depth > 10:
                depth = 10
            if depth < 1:
                depth = 1
            
            tree = []
            for current_root, dir_names, file_names in os.walk(safe_path, followlinks=False):
                current_path = Path(current_root)
                current_depth = len(current_path.relative_to(safe_path).parts)
                if current_depth >= depth:
                    dir_names[:] = []  # Don't recurse deeper
                
                entries = [current_path / name for name in dir_names + file_names]
                for item in entries:
                    rel_depth = len(item.relative_to(safe_path).parts)
                    if rel_depth > depth:
                        continue
                    try:
                        stat = item.stat()
                        tree.append({
                            "name": item.name,
                            "path": str(item.relative_to(project_root)),
                            "is_dir": item.is_dir(),
                            "size": stat.st_size if item.is_file() else 0
                        })
                    except (OSError, PermissionError):
                        # Skip files we can't stat
                        continue
            
            # Sort: directories first, then files
            tree.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
            
            return ToolResult(success=True, data={
                "path": str(safe_path.relative_to(project_root)),
                "tree": tree
            })
        except Exception as e:
            return ToolResult(success=False, error=str(e))