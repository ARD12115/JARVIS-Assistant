import subprocess
import tempfile
import os
import sys
from typing import Any
from src_python.tools.base import Tool, ToolResult


class CodeExecTool(Tool):
    name = "code_exec"
    description = "Execute Python code in a sandboxed subprocess"
    parameters = {
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "Python code to execute"},
            "timeout": {"type": "integer", "description": "Timeout in seconds", "default": 30}
        },
        "required": ["code"]
    }
    returns = {
        "type": "object",
        "properties": {
            "stdout": {"type": "string"},
            "stderr": {"type": "string"},
            "return_code": {"type": "integer"},
            "timed_out": {"type": "boolean"}
        }
    }

    def __init__(self, isolated: bool = False):
        self.isolated = isolated

    def execute(self, code: str, timeout: int = 30) -> ToolResult:
        if not self.isolated:
            return ToolResult(
                success=False,
                error="Code execution is disabled because no isolated sandbox is configured",
            )
        try:
            # Create a temporary file for the code
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
                f.write(code)
                temp_path = f.name
            
            try:
                # Run in subprocess with restricted environment
                env = os.environ.copy()
                # Remove sensitive env vars
                for key in list(env.keys()):
                    if any(s in key.upper() for s in ["KEY", "TOKEN", "SECRET", "PASSWORD", "API"]):
                        env.pop(key, None)
                
                result = subprocess.run(
                    [sys.executable, temp_path],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    env=env,
                    cwd=os.getcwd()
                )
                
                return ToolResult(success=True, data={
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "return_code": result.returncode,
                    "timed_out": False
                })
            except subprocess.TimeoutExpired:
                return ToolResult(success=True, data={
                    "stdout": "",
                    "stderr": f"Execution timed out after {timeout} seconds",
                    "return_code": -1,
                    "timed_out": True
                })
            finally:
                # Clean up temp file
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass
                    
        except Exception as e:
            return ToolResult(success=False, error=str(e))