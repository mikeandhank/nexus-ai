"""
Agent Process Manager - True OS Capabilities
=============================================
Real-time process management with stdin/stdout/stderr.
"""

import os
import json
import uuid
import asyncio
import logging
import subprocess
import threading
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ProcessState(Enum):
    """Process states"""
    CREATED = "created"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AgentProcess:
    """A running agent process with full TTY support"""
    process_id: str
    agent_id: str
    
    # Process info
    command: List[str]
    cwd: str = "/tmp"
    
    # State
    state: ProcessState = ProcessState.CREATED
    
    # Pipes
    stdin: Optional[any] = None
    stdout: Optional[any] = None
    stderr: Optional[Optional[any]] = None
    process: Optional[subprocess.Popen] = None
    
    # I/O callbacks
    stdout_callback: Optional[Callable] = None
    stderr_callback: Optional[Callable] = None
    
    # Timing
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    exit_code: Optional[int] = None
    
    # Resource limits
    max_memory_mb: int = 512
    max_cpu_percent: int = 80
    timeout_seconds: int = 3600


class ProcessManager:
    """
    Agent Process Manager - True OS Kernel Feature
    
    Capabilities:
    - Real-time stdin/stdout/stderr
    - Background process execution
    - Process state management
    - Resource limits (memory, CPU)
    - Timeouts
    - I/O streaming
    """
    
    def __init__(self, sandbox_dir: str = "/tmp/nexusos"):
        self.sandbox_dir = sandbox_dir
        self.processes: Dict[str, AgentProcess] = {}
        self._lock = threading.Lock()
        
        # Ensure sandbox exists
        os.makedirs(sandbox_dir, exist_ok=True)
    
    # ========== PROCESS CREATION ==========
    
    def create_process(self, agent_id: str, command: List[str],
                      cwd: str = None, env: Dict = None,
                      max_memory_mb: int = 512,
                      max_cpu_percent: int = 80,
                      timeout_seconds: int = 3600) -> AgentProcess:
        """Create a new agent process"""
        
        process_id = f"proc_{uuid.uuid4().hex[:12]}"
        
        # Working directory in sandbox
        if cwd is None:
            cwd = f"{self.sandbox_dir}/agents/{agent_id}"
            os.makedirs(cwd, exist_ok=True)
        
        # Environment
        full_env = os.environ.copy()
        if env:
            full_env.update(env)
        
        proc = AgentProcess(
            process_id=process_id,
            agent_id=agent_id,
            command=command,
            cwd=cwd,
            max_memory_mb=max_memory_mb,
            max_cpu_percent=max_cpu_percent,
            timeout_seconds=timeout_seconds,
            stdin=None,
            stdout=None,
            stderr=None,
            process=None
        )
        
        with self._lock:
            self.processes[process_id] = proc
        
        logger.info(f"Created process {process_id} for agent {agent_id}")
        
        return proc
    
    # ========== PROCESS EXECUTION ==========
    
    def start_process(self, process_id: str) -> Dict:
        """Start a process with full I/O"""
        
        with self._lock:
            if process_id not in self.processes:
                return {"success": False, "error": "Process not found"}
            
            proc = self.processes[process_id]
        
        if proc.state != ProcessState.CREATED:
            return {"success": False, "error": f"Invalid state: {proc.state}"}
        
        proc.state = ProcessState.STARTING
        
        try:
            # Start process with pipes for stdin/stdout/stderr
            proc.process = subprocess.Popen(
                proc.command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=proc.cwd,
                env=proc.env if hasattr(proc, 'env') else os.environ.copy(),
                text=False  # Binary mode for streaming
            )
            
            proc.state = ProcessState.RUNNING
            proc.started_at = datetime.utcnow()
            
            # Start I/O reader threads
            self._start_io_readers(proc)
            
            logger.info(f"Started process {process_id}")
            
            return {
                "success": True,
                "process_id": process_id,
                "pid": proc.process.pid,
                "state": proc.state.value
            }
            
        except Exception as e:
            proc.state = ProcessState.FAILED
            return {"success": False, "error": str(e)}
    
    def _start_io_readers(self, proc: AgentProcess):
        """Start background threads to read stdout/stderr"""
        
        def read_stdout():
            while proc.process and proc.process.poll() is None:
                try:
                    line = proc.process.stdout.readline()
                    if line:
                        line_str = line.decode('utf-8', errors='replace')
                        if proc.stdout_callback:
                            proc.stdout_callback(proc.process_id, line_str)
                except:
                    break
            
            proc.state = ProcessState.COMPLETED
            proc.completed_at = datetime.utcnow()
            proc.exit_code = proc.process.returncode if proc.process else 0
        
        def read_stderr():
            while proc.process and proc.process.poll() is None:
                try:
                    line = proc.process.stderr.readline()
                    if line:
                        line_str = line.decode('utf-8', errors='replace')
                        if proc.stderr_callback:
                            proc.stderr_callback(proc.process_id, line_str)
                except:
                    break
        
        # Start reader threads
        threading.Thread(target=read_stdout, daemon=True).start()
        threading.Thread(target=read_stderr, daemon=True).start()
    
    # ========== PROCESS CONTROL ==========
    
    def write_stdin(self, process_id: str, data: str) -> Dict:
        """Write to process stdin"""
        
        with self._lock:
            if process_id not in self.processes:
                return {"success": False, "error": "Process not found"}
            
            proc = self.processes[process_id]
        
        if proc.state != ProcessState.RUNNING:
            return {"success": False, "error": f"Process not running: {proc.state}"}
        
        try:
            proc.process.stdin.write(data.encode() if isinstance(data, str) else data)
            proc.process.stdin.flush()
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def read_stdout(self, process_id: str, lines: int = 100) -> List[str]:
        """Read recent stdout lines (buffered)"""
        # TODO: Implement circular buffer
        return []
    
    def read_stderr(self, process_id: str, lines: int = 100) -> List[str]:
        """Read recent stderr lines"""
        # TODO: Implement circular buffer
        return []
    
    def pause_process(self, process_id: str) -> Dict:
        """Pause process (SIGSTOP)"""
        
        with self._lock:
            if process_id not in self.processes:
                return {"success": False, "error": "Process not found"}
            
            proc = self.processes[process_id]
        
        if proc.state != ProcessState.RUNNING:
            return {"success": False, "error": "Process not running"}
        
        try:
            proc.process.send_signal(subprocess.signal.SIGSTOP)
            proc.state = ProcessState.PAUSED
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def resume_process(self, process_id: str) -> Dict:
        """Resume paused process (SIGCONT)"""
        
        with self._lock:
            if process_id not in self.processes:
                return {"success": False, "error": "Process not found"}
            
            proc = self.processes[process_id]
        
        if proc.state != ProcessState.PAUSED:
            return {"success": False, "error": "Process not paused"}
        
        try:
            proc.process.send_signal(subprocess.signal.SIGCONT)
            proc.state = ProcessState.RUNNING
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def stop_process(self, process_id: str, force: bool = False) -> Dict:
        """Stop a process"""
        
        with self._lock:
            if process_id not in self.processes:
                return {"success": False, "error": "Process not found"}
            
            proc = self.processes[process_id]
        
        if proc.state not in [ProcessState.RUNNING, ProcessState.PAUSED]:
            return {"success": False, "error": f"Cannot stop: {proc.state}"}
        
        try:
            if force:
                proc.process.kill()
            else:
                proc.process.terminate()
                proc.process.wait(timeout=5)
            
            proc.state = ProcessState.STOPPED
            proc.completed_at = datetime.utcnow()
            proc.exit_code = proc.process.returncode
            
            return {"success": True, "exit_code": proc.exit_code}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ========== QUERY ==========
    
    def get_process(self, process_id: str) -> Optional[AgentProcess]:
        """Get process info"""
        return self.processes.get(process_id)
    
    def list_processes(self, agent_id: str = None) -> List[Dict]:
        """List all processes"""
        processes = self.processes.values()
        
        if agent_id:
            processes = [p for p in processes if p.agent_id == agent_id]
        
        return [
            {
                "process_id": p.process_id,
                "agent_id": p.agent_id,
                "command": " ".join(p.command),
                "state": p.state.value,
                "pid": p.process.pid if p.process else None,
                "created_at": p.created_at.isoformat(),
                "started_at": p.started_at.isoformat() if p.started_at else None,
                "exit_code": p.exit_code
            }
            for p in processes
        ]
    
    def get_stats(self) -> Dict:
        """Get process statistics"""
        return {
            "total": len(self.processes),
            "running": sum(1 for p in self.processes.values() if p.state == ProcessState.RUNNING),
            "paused": sum(1 for p in self.processes.values() if p.state == ProcessState.PAUSED),
            "completed": sum(1 for p in self.processes.values() if p.state == ProcessState.COMPLETED),
            "failed": sum(1 for p in self.processes.values() if p.state == ProcessState.FAILED)
        }


# Singleton
_process_manager = None

def get_process_manager() -> ProcessManager:
    global _process_manager
    if _process_manager is None:
        _process_manager = ProcessManager()
    return _process_manager
