"""
NexusOS Agent Kernel - The Core Operating System
================================================
This is the heart of a true Agent Operating System.

It treats agents as first-class processes with:
- Lifecycle management
- Resource allocation
- Security sandboxing
- IPC (inter-process communication)
- File system isolation
- Network isolation
"""

import os
import json
import time
import uuid
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import threading
import subprocess
import psycopg2
from psycopg2.extras import RealDictCursor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AgentState(Enum):
    """Agent lifecycle states"""
    CREATED = "created"
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"


@dataclass
class AgentProcess:
    """
    Represents an agent as a first-class OS process.
    
    Similar to a process in a traditional OS, but for AI agents.
    """
    agent_id: str
    user_id: str
    name: str
    state: AgentState = AgentState.CREATED
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None
    
    # Resources
    cpu_percent: float = 0
    memory_mb: int = 0
    threads: int = 0
    
    # Limits
    max_cpu_percent: int = 100
    max_memory_mb: int = 512
    max_disk_mb: int = 100
    max_network_mb: int = 50
    
    # Filesystem
    workspace_dir: str = ""
    allowed_paths: List[str] = field(default_factory=list)
    
    # Network
    network_isolated: bool = False
    allowed_ports: List[int] = field(default_factory=list)
    
    # Security
    sandboxed: bool = False
    trusted: bool = False
    capabilities: List[str] = field(default_factory=list)
    
    # Stats
    requests_served: int = 0
    tokens_used: int = 0
    uptime_seconds: int = 0
    
    # Process handle (for actual subprocess)
    process_handle: Any = None


class AgentKernel:
    """
    THE KERNEL - Core of the Agent Operating System
    
    Manages agents as processes with:
    - Scheduling
    - Resource allocation
    - Security enforcement
    - IPC
    - Filesystem
    - Networking
    """
    
    def __init__(self, db_url: str = None, workspace_root: str = "/opt/nexusos-agent-workspaces"):
        self.db_url = db_url or os.environ.get('DATABASE_URL',
            'postgresql://nexusos:nexusos@localhost:5432/nexusos')
        self.workspace_root = workspace_root
        
        # In-memory process table
        self.processes: Dict[str, AgentProcess] = {}
        
        # IPC message bus
        self.message_bus: Dict[str, List[Dict]] = {}
        
        # Event handlers
        self.event_handlers: Dict[str, List[Callable]] = {}
        
        # Scheduler loop
        self.scheduler_running = False
        self.scheduler_thread = None
        
        # Initialize
        self._init_db()
        self._load_running_agents()
        
        logger.info("NexusOS Kernel initialized")
    
    def _get_conn(self):
        return psycopg2.connect(self.db_url, cursor_factory=RealDictCursor)
    
    def _init_db(self):
        """Initialize kernel tables"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # Agent processes table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS kernel_agents (
                agent_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                state TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT NOW(),
                started_at TIMESTAMP,
                stopped_at TIMESTAMP,
                max_cpu_percent INTEGER DEFAULT 100,
                max_memory_mb INTEGER DEFAULT 512,
                max_disk_mb INTEGER DEFAULT 100,
                max_network_mb INTEGER DEFAULT 50,
                workspace_dir TEXT,
                allowed_paths TEXT,
                network_isolated BOOLEAN DEFAULT FALSE,
                allowed_ports TEXT,
                sandboxed BOOLEAN DEFAULT FALSE,
                trusted BOOLEAN DEFAULT FALSE,
                capabilities TEXT,
                requests_served INTEGER DEFAULT 0,
                tokens_used INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # System events
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS kernel_events (
                id SERIAL PRIMARY KEY,
                agent_id TEXT,
                event_type TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT NOW(),
                data TEXT
            )
        """)
        
        # IPC messages
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS kernel_ipc (
                id SERIAL PRIMARY KEY,
                from_agent_id TEXT NOT NULL,
                to_agent_id TEXT,
                message_type TEXT NOT NULL,
                payload TEXT,
                timestamp TIMESTAMP DEFAULT NOW(),
                delivered BOOLEAN DEFAULT FALSE
            )
        """)
        
        conn.commit()
        conn.close()
    
    def _load_running_agents(self):
        """Load running agents from DB on startup"""
        conn = self._get_conn()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT * FROM kernel_agents 
            WHERE state IN ('running', 'paused')
        """)
        
        for row in cursor.fetchall():
            proc = self._row_to_process(row)
            self.processes[proc.agent_id] = proc
            logger.info(f"Loaded agent {proc.agent_id} in state {proc.state}")
        
        conn.close()
    
    def _row_to_process(self, row: Dict) -> AgentProcess:
        """Convert DB row to AgentProcess"""
        return AgentProcess(
            agent_id=row['agent_id'],
            user_id=row['user_id'],
            name=row['name'],
            state=AgentState(row['state']),
            created_at=row['created_at'],
            started_at=row.get('started_at'),
            stopped_at=row.get('stopped_at'),
            max_cpu_percent=row.get('max_cpu_percent', 100),
            max_memory_mb=row.get('max_memory_mb', 512),
            max_disk_mb=row.get('max_disk_mb', 100),
            max_network_mb=row.get('max_network_mb', 50),
            workspace_dir=row.get('workspace_dir', ''),
            allowed_paths=json.loads(row.get('allowed_paths', '[]')),
            network_isolated=row.get('network_isolated', False),
            allowed_ports=json.loads(row.get('allowed_ports', '[]')),
            sandboxed=row.get('sandboxed', False),
            trusted=row.get('trusted', False),
            capabilities=json.loads(row.get('capabilities', '[]')),
            requests_served=row.get('requests_served', 0),
            tokens_used=row.get('tokens_used', 0)
        )
    
    # ========== LIFECYCLE MANAGEMENT ==========
    
    def create_agent(self, user_id: str, name: str, config: Dict = None) -> AgentProcess:
        """Create a new agent process"""
        config = config or {}
        
        agent_id = f"agent_{uuid.uuid4().hex[:12]}"
        
        # Create workspace directory
        workspace_dir = os.path.join(self.workspace_root, user_id, agent_id)
        os.makedirs(workspace_dir, exist_ok=True)
        
        proc = AgentProcess(
            agent_id=agent_id,
            user_id=user_id,
            name=name,
            state=AgentState.CREATED,
            workspace_dir=workspace_dir,
            allowed_paths=[workspace_dir],
            max_cpu_percent=config.get('max_cpu_percent', 100),
            max_memory_mb=config.get('max_memory_mb', 512),
            max_disk_mb=config.get('max_disk_mb', 100),
            max_network_mb=config.get('max_network_mb', 50),
            network_isolated=config.get('network_isolated', False),
            sandboxed=config.get('sandboxed', True),
            capabilities=config.get('capabilities', ['chat', 'memory'])
        )
        
        # Save to DB
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO kernel_agents 
            (agent_id, user_id, name, state, workspace_dir, allowed_paths,
             max_cpu_percent, max_memory_mb, max_disk_mb, max_network_mb,
             network_isolated, sandboxed, capabilities)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (proc.agent_id, proc.user_id, proc.name, proc.state.value,
              proc.workspace_dir, json.dumps(proc.allowed_paths),
              proc.max_cpu_percent, proc.max_memory_mb, proc.max_disk_mb, proc.max_network_mb,
              proc.network_isolated, proc.sandboxed, json.dumps(proc.capabilities)))
        conn.commit()
        conn.close()
        
        # Add to process table
        self.processes[agent_id] = proc
        
        self._emit_event(agent_id, "created", {"name": name})
        
        logger.info(f"Created agent {agent_id} for user {user_id}")
        return proc
    
    def start_agent(self, agent_id: str) -> Dict:
        """Start an agent (transition from created -> running)"""
        if agent_id not in self.processes:
            return {"success": False, "error": "Agent not found"}
        
        proc = self.processes[agent_id]
        
        if proc.state not in [AgentState.CREATED, AgentState.PAUSED]:
            return {"success": False, "error": f"Cannot start from state {proc.state}"}
        
        # Transition to running
        proc.state = AgentState.RUNNING
        proc.started_at = datetime.utcnow()
        
        # Update DB
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE kernel_agents SET state = 'running', started_at = NOW()
            WHERE agent_id = %s
        """, (agent_id,))
        conn.commit()
        conn.close()
        
        self._emit_event(agent_id, "started", {})
        
        logger.info(f"Started agent {agent_id}")
        return {"success": True, "agent_id": agent_id, "state": proc.state.value}
    
    def stop_agent(self, agent_id: str) -> Dict:
        """Stop an agent gracefully"""
        if agent_id not in self.processes:
            return {"success": False, "error": "Agent not found"}
        
        proc = self.processes[agent_id]
        
        if proc.state != AgentState.RUNNING:
            return {"success": False, "error": f"Agent not running"}
        
        proc.state = AgentState.STOPPING
        
        # Update DB
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE kernel_agents SET state = 'stopped', stopped_at = NOW()
            WHERE agent_id = %s
        """, (agent_id,))
        conn.commit()
        conn.close()
        
        proc.state = AgentState.STOPPED
        proc.stopped_at = datetime.utcnow()
        
        self._emit_event(agent_id, "stopped", {})
        
        logger.info(f"Stopped agent {agent_id}")
        return {"success": True, "agent_id": agent_id}
    
    def pause_agent(self, agent_id: str) -> Dict:
        """Pause an agent (freeze state)"""
        if agent_id not in self.processes:
            return {"success": False, "error": "Agent not found"}
        
        proc = self.processes[agent_id]
        
        if proc.state != AgentState.RUNNING:
            return {"success": False, "error": "Agent not running"}
        
        proc.state = AgentState.PAUSED
        
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("UPDATE kernel_agents SET state = 'paused' WHERE agent_id = %s", (agent_id,))
        conn.commit()
        conn.close()
        
        self._emit_event(agent_id, "paused", {})
        
        return {"success": True, "state": "paused"}
    
    def get_agent(self, agent_id: str) -> Optional[AgentProcess]:
        """Get agent process info"""
        return self.processes.get(agent_id)
    
    def list_agents(self, user_id: str = None, state: AgentState = None) -> List[AgentProcess]:
        """List agents with optional filters"""
        result = []
        for proc in self.processes.values():
            if user_id and proc.user_id != user_id:
                continue
            if state and proc.state != state:
                continue
            result.append(proc)
        return result
    
    # ========== RESOURCE MANAGEMENT ==========
    
    def set_limits(self, agent_id: str, limits: Dict) -> Dict:
        """Set resource limits for agent"""
        if agent_id not in self.processes:
            return {"success": False, "error": "Agent not found"}
        
        proc = self.processes[agent_id]
        
        proc.max_cpu_percent = limits.get('cpu_percent', proc.max_cpu_percent)
        proc.max_memory_mb = limits.get('memory_mb', proc.max_memory_mb)
        proc.max_disk_mb = limits.get('disk_mb', proc.max_disk_mb)
        proc.max_network_mb = limits.get('network_mb', proc.max_network_mb)
        
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE kernel_agents SET 
                max_cpu_percent = %s, max_memory_mb = %s, 
                max_disk_mb = %s, max_network_mb = %s
            WHERE agent_id = %s
        """, (proc.max_cpu_percent, proc.max_memory_mb, 
              proc.max_disk_mb, proc.max_network_mb, agent_id))
        conn.commit()
        conn.close()
        
        return {"success": True}
    
    def get_usage(self, agent_id: str) -> Dict:
        """Get current resource usage for agent"""
        if agent_id not in self.processes:
            return {"error": "Agent not found"}
        
        proc = self.processes[agent_id]
        
        # Calculate uptime
        if proc.started_at:
            uptime = (datetime.utcnow() - proc.started_at).total_seconds()
        else:
            uptime = 0
        
        return {
            "agent_id": agent_id,
            "state": proc.state.value,
            "cpu_percent": proc.cpu_percent,
            "memory_mb": proc.memory_mb,
            "requests_served": proc.requests_served,
            "tokens_used": proc.tokens_used,
            "uptime_seconds": int(uptime),
            "limits": {
                "cpu_percent": proc.max_cpu_percent,
                "memory_mb": proc.max_memory_mb,
                "disk_mb": proc.max_disk_mb,
                "network_mb": proc.max_network_mb
            }
        }
    
    # ========== INTER-PROCESS COMMUNICATION ==========
    
    def send_message(self, from_agent_id: str, to_agent_id: str, 
                    message_type: str, payload: Dict) -> Dict:
        """Send message from one agent to another"""
        # Check sender exists
        if from_agent_id not in self.processes:
            return {"success": False, "error": "Sender not found"}
        
        # Check recipient exists
        if to_agent_id and to_agent_id not in self.processes:
            return {"success": False, "error": "Recipient not found"}
        
        message_id = str(uuid.uuid4())
        
        # Store message
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO kernel_ipc (id, from_agent_id, to_agent_id, message_type, payload)
            VALUES (%s, %s, %s, %s, %s)
        """, (message_id, from_agent_id, to_agent_id, message_type, json.dumps(payload)))
        conn.commit()
        conn.close()
        
        # Deliver to in-memory queue
        if to_agent_id not in self.message_bus:
            self.message_bus[to_agent_id] = []
        
        self.message_bus[to_agent_id].append({
            "id": message_id,
            "from": from_agent_id,
            "type": message_type,
            "payload": payload,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        self._emit_event(from_agent_id, "message_sent", {"to": to_agent_id, "type": message_type})
        
        return {"success": True, "message_id": message_id}
    
    def receive_messages(self, agent_id: str, limit: int = 10) -> List[Dict]:
        """Get messages waiting for an agent"""
        if agent_id not in self.message_bus:
            return []
        
        messages = self.message_bus[agent_id][:limit]
        self.message_bus[agent_id] = self.message_bus[agent_id][limit:]
        
        return messages
    
    def broadcast(self, from_agent_id: str, message_type: str, payload: Dict) -> Dict:
        """Broadcast to all agents"""
        count = 0
        for agent_id in self.processes.keys():
            if agent_id != from_agent_id:
                self.send_message(from_agent_id, agent_id, message_type, payload)
                count += 1
        
        return {"success": True, "delivered": count}
    
    # ========== EVENT SYSTEM ==========
    
    def _emit_event(self, agent_id: str, event_type: str, data: Dict):
        """Emit kernel event"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO kernel_events (agent_id, event_type, data)
            VALUES (%s, %s, %s)
        """, (agent_id, event_type, json.dumps(data)))
        conn.commit()
        conn.close()
        
        # Call handlers
        if event_type in self.event_handlers:
            for handler in self.event_handlers[event_type]:
                try:
                    handler(agent_id, data)
                except Exception as e:
                    logger.error(f"Event handler error: {e}")
    
    def on_event(self, event_type: str, handler: Callable):
        """Register event handler"""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
    
    def get_events(self, agent_id: str = None, limit: int = 100) -> List[Dict]:
        """Get kernel events"""
        conn = self._get_conn()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        if agent_id:
            cursor.execute("""
                SELECT * FROM kernel_events 
                WHERE agent_id = %s
                ORDER BY timestamp DESC LIMIT %s
            """, (agent_id, limit))
        else:
            cursor.execute("""
                SELECT * FROM kernel_events 
                ORDER BY timestamp DESC LIMIT %s
            """, (limit,))
        
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results
    
    # ========== FILESYSTEM (Per-Agent) ==========
    
    def get_workspace(self, agent_id: str) -> str:
        """Get agent's workspace directory"""
        if agent_id not in self.processes:
            return None
        return self.processes[agent_id].workspace_dir
    
    def check_path_access(self, agent_id: str, path: str) -> bool:
        """Check if agent can access path"""
        if agent_id not in self.processes:
            return False
        
        proc = self.processes[agent_id]
        
        # Trusted agents can access anything
        if proc.trusted:
            return True
        
        # Check against allowed paths
        for allowed in proc.allowed_paths:
            if path.startswith(allowed):
                return True
        
        return False
    
    # ========== NETWORK (Per-Agent) ==========
    
    def is_network_isolated(self, agent_id: str) -> bool:
        """Check if agent is network isolated"""
        if agent_id not in self.processes:
            return False
        return self.processes[agent_id].network_isolated
    
    def check_port_access(self, agent_id: str, port: int) -> bool:
        """Check if agent can use port"""
        if agent_id not in self.processes:
            return False
        
        proc = self.processes[agent_id]
        
        # No restrictions
        if not proc.network_isolated:
            return True
        
        # Check allowed ports
        if not proc.allowed_ports:
            return False
        
        return port in proc.allowed_ports
    
    # ========== SYSTEM STATUS ==========
    
    def get_kernel_stats(self) -> Dict:
        """Get overall kernel statistics"""
        states = {}
        for proc in self.processes.values():
            state = proc.state.value
            states[state] = states.get(state, 0) + 1
        
        return {
            "total_agents": len(self.processes),
            "states": states,
            "workspace_root": self.workspace_root,
            "scheduler_running": self.scheduler_running
        }


# Singleton
_kernel = None

def get_kernel(db_url: str = None) -> AgentKernel:
    global _kernel
    if _kernel is None:
        _kernel = AgentKernel(db_url)
    return _kernel