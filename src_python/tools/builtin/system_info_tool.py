import psutil
import platform
from typing import Any
from src_python.tools.base import Tool, ToolResult


class SystemInfoTool(Tool):
    name = "system_info"
    description = "Get system information (CPU, RAM, GPU, disk)"
    parameters = {
        "type": "object",
        "properties": {},
        "required": []
    }
    returns = {
        "type": "object",
        "properties": {
            "cpu_percent": {"type": "number"},
            "cpu_count": {"type": "integer"},
            "ram_total_gb": {"type": "number"},
            "ram_used_gb": {"type": "number"},
            "ram_percent": {"type": "number"},
            "disk_total_gb": {"type": "number"},
            "disk_used_gb": {"type": "number"},
            "disk_percent": {"type": "number"},
            "gpu_name": {"type": "string"},
            "gpu_memory_total_mb": {"type": "integer"},
            "gpu_memory_used_mb": {"type": "integer"},
            "os": {"type": "string"},
            "python_version": {"type": "string"}
        }
    }

    def execute(self) -> ToolResult:
        try:
            # CPU
            cpu_percent = psutil.cpu_percent(interval=0.5)
            cpu_count = psutil.cpu_count()
            
            # RAM
            ram = psutil.virtual_memory()
            ram_total_gb = round(ram.total / (1024**3), 2)
            ram_used_gb = round(ram.used / (1024**3), 2)
            ram_percent = ram.percent
            
            # Disk
            disk = psutil.disk_usage("/")
            disk_total_gb = round(disk.total / (1024**3), 2)
            disk_used_gb = round(disk.used / (1024**3), 2)
            disk_percent = round((disk.used / disk.total) * 100, 1)
            
            # GPU (optional)
            gpu_name = "N/A"
            gpu_memory_total_mb = 0
            gpu_memory_used_mb = 0
            try:
                import GPUtil
                gpus = GPUtil.getGPUs()
                if gpus:
                    gpu = gpus[0]
                    gpu_name = gpu.name
                    gpu_memory_total_mb = gpu.memoryTotal
                    gpu_memory_used_mb = gpu.memoryUsed
            except Exception:
                pass
            
            return ToolResult(success=True, data={
                "cpu_percent": cpu_percent,
                "cpu_count": cpu_count,
                "ram_total_gb": ram_total_gb,
                "ram_used_gb": ram_used_gb,
                "ram_percent": ram_percent,
                "disk_total_gb": disk_total_gb,
                "disk_used_gb": disk_used_gb,
                "disk_percent": disk_percent,
                "gpu_name": gpu_name,
                "gpu_memory_total_mb": gpu_memory_total_mb,
                "gpu_memory_used_mb": gpu_memory_used_mb,
                "os": f"{platform.system()} {platform.release()}",
                "python_version": platform.python_version()
            })
        except Exception as e:
            return ToolResult(success=False, error=str(e))