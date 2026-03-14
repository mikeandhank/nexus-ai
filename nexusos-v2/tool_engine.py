"""
NexusOS v2 - Tool Execution Engine

Provides actual tool execution capabilities:
- File system operations
- Process execution
- HTTP requests
- Custom tool registration
"""

import os
import sys
import json
import subprocess
import requests
import tempfile
import shutil
from typing import Dict, List, Any, Callable, Optional
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ToolResult:
    """Result of a tool execution."""
    
    def __init__(self, success: bool, result: Any = None, error: str = None, 
                 execution_time_ms: float = 0):
        self.success = success
        self.result = result
        self.error = error
        self.execution_time_ms = execution_time_ms
    
    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms
        }


class ToolEngine:
    """
    Tool execution engine for NexusOS.
    
    Provides:
    - File system operations (read, write, list, etc.)
    - Process execution
    - HTTP requests
    - Custom tool registration
    """
    
    def __init__(self, workspace_dir: str = None):
        self.workspace_dir = workspace_dir or os.environ.get("NEXUSOS_WORKSPACE", "/opt/nexusos-workspace")
        os.makedirs(self.workspace_dir, exist_ok=True)
        
        # Registered tools
        self.tools: Dict[str, Callable] = {}
        
        # Register default tools
        self._register_default_tools()
    
    def _register_default_tools(self):
        """Register default tools."""
        
        # File operations
        self.register_tool("file_read", self._tool_file_read)
        self.register_tool("file_write", self._tool_file_write)
        self.register_tool("file_list", self._tool_file_list)
        self.register_tool("file_exists", self._tool_file_exists)
        self.register_tool("file_delete", self._tool_file_delete)
        self.register_tool("file_mkdir", self._tool_file_mkdir)
        
        # Process operations
        self.register_tool("process_run", self._tool_process_run)
        
        # HTTP operations
        self.register_tool("http_get", self._tool_http_get)
        self.register_tool("http_post", self._tool_http_post)
        
        # System operations
        self.register_tool("system_info", self._tool_system_info)
        self.register_tool("shell_command", self._tool_shell_command)
        
        # Search
        self.register_tool("search_files", self._tool_search_files)
        
        logger.info(f"Registered {len(self.tools)} default tools")
    
    def register_tool(self, name: str, func: Callable):
        """Register a custom tool."""
        self.tools[name] = func
        logger.info(f"Registered tool: {name}")
    
    def unregister_tool(self, name: str):
        """Unregister a tool."""
        if name in self.tools:
            del self.tools[name]
            logger.info(f"Unregistered tool: {name}")
    
    def list_tools(self) -> List[str]:
        """List all available tools."""
        return list(self.tools.keys())
    
    def execute_tool(self, tool_name: str, **kwargs) -> ToolResult:
        """Execute a tool with given parameters."""
        import time
        start_time = time.time()
        
        if tool_name not in self.tools:
            return ToolResult(
                success=False,
                error=f"Tool '{tool_name}' not found. Available: {self.list_tools()}"
            )
        
        try:
            tool_func = self.tools[tool_name]
            result = tool_func(**kwargs)
            execution_time = (time.time() - start_time) * 1000
            
            return ToolResult(
                success=True,
                result=result,
                execution_time_ms=execution_time
            )
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f"Tool execution error: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                execution_time_ms=execution_time
            )
    
    # File tools
    def _tool_file_read(self, path: str, max_chars: int = 50000) -> str:
        """Read file contents."""
        full_path = os.path.join(self.workspace_dir, path) if not path.startswith('/') else path
        
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"File not found: {path}")
        
        with open(full_path, 'r') as f:
            content = f.read(max_chars)
        
        if len(content) >= max_chars:
            content += f"\n... (truncated at {max_chars} chars)"
        
        return content
    
    def _tool_file_write(self, path: str, content: str, mode: str = 'w') -> Dict:
        """Write content to file."""
        full_path = os.path.join(self.workspace_dir, path) if not path.startswith('/') else path
        
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        with open(full_path, mode) as f:
            f.write(content)
        
        return {"path": path, "size": len(content)}
    
    def _tool_file_list(self, path: str = ".", pattern: str = "*") -> List[Dict]:
        """List files in directory."""
        import fnmatch
        
        full_path = os.path.join(self.workspace_dir, path) if not path.startswith('/') else path
        
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"Path not found: {path}")
        
        results = []
        
        if os.path.isfile(full_path):
            return [{"name": os.path.basename(full_path), "type": "file", "size": os.path.getsize(full_path)}]
        
        for item in os.listdir(full_path):
            if fnmatch.fnmatch(item, pattern):
                item_path = os.path.join(full_path, item)
                results.append({
                    "name": item,
                    "type": "dir" if os.path.isdir(item_path) else "file",
                    "size": os.path.getsize(item_path) if os.path.isfile(item_path) else 0
                })
        
        return results
    
    def _tool_file_exists(self, path: str) -> bool:
        """Check if file exists."""
        full_path = os.path.join(self.workspace_dir, path) if not path.startswith('/') else path
        return os.path.exists(full_path)
    
    def _tool_file_delete(self, path: str) -> Dict:
        """Delete file or directory."""
        full_path = os.path.join(self.workspace_dir, path) if not path.startswith('/') else path
        
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"Path not found: {path}")
        
        if os.path.isfile(full_path):
            os.remove(full_path)
        else:
            shutil.rmtree(full_path)
        
        return {"deleted": path}
    
    def _tool_file_mkdir(self, path: str) -> Dict:
        """Create directory."""
        full_path = os.path.join(self.workspace_dir, path) if not path.startswith('/') else path
        os.makedirs(full_path, exist_ok=True)
        return {"created": path}
    
    # Process tools
    def _tool_process_run(self, command: str, cwd: str = None, timeout: int = 30, 
                         env: Dict = None) -> Dict:
        """Run a shell command."""
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd or self.workspace_dir,
            capture_output=True,
            timeout=timeout,
            env={**os.environ, **(env or {})}
        )
        
        return {
            "returncode": result.returncode,
            "stdout": result.stdout.decode('utf-8', errors='replace'),
            "stderr": result.stderr.decode('utf-8', errors='replace'),
        }
    
    def _tool_shell_command(self, command: str) -> str:
        """Run a simple shell command."""
        result = subprocess.run(command, shell=True, capture_output=True, timeout=30)
        output = result.stdout.decode('utf-8', errors='replace')
        if result.returncode != 0 and not output:
            output = result.stderr.decode('utf-8', errors='replace')
        return output
    
    # HTTP tools
    def _tool_http_get(self, url: str, headers: Dict = None, timeout: int = 30) -> Dict:
        """Make HTTP GET request."""
        response = requests.get(url, headers=headers or {}, timeout=timeout)
        return {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "content": response.text[:10000],
        }
    
    def _tool_http_post(self, url: str, data: Dict = None, json: Dict = None, 
                       headers: Dict = None, timeout: int = 30) -> Dict:
        """Make HTTP POST request."""
        response = requests.post(url, data=data, json=json, headers=headers, timeout=timeout)
        return {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "content": response.text[:10000],
        }
    
    # System tools
    def _tool_system_info(self) -> Dict:
        """Get system information."""
        import platform
        return {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "platform_release": platform.release(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
            "hostname": platform.node(),
        }
    
    # Search tools
    def _tool_search_files(self, query: str, path: str = None) -> List[Dict]:
        """Search files by content."""
        import fnmatch
        
        search_path = path or self.workspace_dir
        results = []
        
        for root, dirs, files in os.walk(search_path):
            for filename in files:
                filepath = os.path.join(root, filename)
                
                # Skip binary files
                if any(filepath.endswith(ext) for ext in ['.pyc', '.so', '.dll', '.exe']):
                    continue
                
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        for i, line in enumerate(f, 1):
                            if query.lower() in line.lower():
                                results.append({
                                    "file": filepath,
                                    "line": i,
                                    "content": line.strip()[:200]
                                })
                                if len(results) >= 50:
                                    return results
                except:
                    pass
        
        return results


# Global instance
_tool_engine = None

def get_tool_engine(workspace_dir: str = None) -> ToolEngine:
    """Get tool engine singleton."""
    global _tool_engine
    if _tool_engine is None:
        _tool_engine = ToolEngine(workspace_dir)
    return _tool_engine
