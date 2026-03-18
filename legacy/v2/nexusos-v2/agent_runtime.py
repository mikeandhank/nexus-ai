"""
Agent Lifecycle Manager for NexusOS
"""
import uuid
import json
import time
import threading
from enum import Enum
from dataclasses import dataclass
from typing import Optional, List, Dict
from datetime import datetime

class AgentStatus(Enum):
    CREATED = "created"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"

@dataclass
class Agent:
    id: str
    user_id: str
    name: str
    role: str = "general"
    system_prompt: str = ""
    model: str = "phi3"
    tools: List = None
    status: str = "created"
    created_at: str = None
    updated_at: str = None
    
    def __post_init__(self):
        if self.tools is None:
            self.tools = []
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()
        self.updated_at = datetime.utcnow().isoformat()

class AgentRuntime:
    def __init__(self, llm_manager=None, tool_engine=None, db=None):
        self.llm_manager = llm_manager
        self.tool_engine = tool_engine
        self.db = db
        self.agents = {}
        self.running_agents = {}
        self.stop_events = {}
        self.agent_history = {}
        
        # Load persisted agents from database on startup
        self._load_agents_from_db()
    
    def _load_agents_from_db(self):
        """Load agents from database on startup"""
        if not self.db:
            return
        try:
            # Use PostgreSQL-style queries (%s instead of ?)
            with self.db._get_conn() as conn:
                c = conn.cursor()
                c.execute("SELECT id, user_id, name, role, system_prompt, model, tools, status FROM agents")
                rows = c.fetchall()
                for row in rows:
                    # Handle both tuple and dict-style rows
                    if isinstance(row, dict):
                        agent = Agent(
                            id=row['id'],
                            user_id=row['user_id'],
                            name=row['name'],
                            role=row.get('role') or "general",
                            system_prompt=row.get('system_prompt') or "",
                            model=row.get('model') or "phi3",
                            tools=json.loads(row['tools']) if row.get('tools') else [],
                            status=row.get('status') or "created"
                        )
                    else:
                        agent = Agent(
                            id=row[0],
                            user_id=row[1],
                            name=row[2],
                            role=row[3] or "general",
                            system_prompt=row[4] or "",
                            model=row[5] or "phi3",
                            tools=json.loads(row[6]) if row[6] else [],
                            status=row[7] or "created"
                        )
                    self.agents[agent.id] = agent
                    self.agent_history[agent.id] = []
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Could not load agents from DB: {e}")
        
    def create_agent(self, user_id, name, role="general", system_prompt="", model="phi3", tools=None):
        agent_id = str(uuid.uuid4())
        agent = Agent(agent_id, user_id, name, role, system_prompt, model, tools or [], "created")
        self.agents[agent_id] = agent
        self.agent_history[agent_id] = []
        
        # Persist to database
        self._save_agent_to_db(agent)
        
        return agent
    
    def _save_agent_to_db(self, agent):
        """Persist agent to database"""
        if not self.db:
            return
        try:
            # Use PostgreSQL-style queries (%s instead of ?)
            with self.db._get_conn() as conn:
                c = conn.cursor()
                c.execute("""
                    INSERT INTO agents 
                    (id, user_id, name, role, system_prompt, model, tools, status, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        user_id = EXCLUDED.user_id,
                        name = EXCLUDED.name,
                        role = EXCLUDED.role,
                        system_prompt = EXCLUDED.system_prompt,
                        model = EXCLUDED.model,
                        tools = EXCLUDED.tools,
                        status = EXCLUDED.status,
                        updated_at = EXCLUDED.updated_at
                """, (
                    agent.id, agent.user_id, agent.name, agent.role,
                    agent.system_prompt, agent.model, json.dumps(agent.tools),
                    agent.status, agent.created_at, agent.updated_at
                ))
                conn.commit()
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Could not save agent to DB: {e}")
    
    def get_agent(self, agent_id):
        return self.agents.get(agent_id)
    
    def list_agents(self, user_id=None):
        if user_id:
            return [a for a in self.agents.values() if a.user_id == user_id]
        return list(self.agents.values())
    
    def start_agent(self, agent_id, initial_message=""):
        agent = self.agents.get(agent_id)
        if not agent:
            return {"error": "Not found"}, 404
        self.stop_events[agent_id] = threading.Event()
        agent.status = AgentStatus.RUNNING.value
        agent.updated_at = datetime.utcnow().isoformat()
        self._save_agent_to_db(agent)
        return {"status": "started", "agent_id": agent_id}
    
    def pause_agent(self, agent_id):
        agent = self.agents.get(agent_id)
        if not agent:
            return {"error": "Not found"}, 404
        agent.status = AgentStatus.PAUSED.value
        agent.updated_at = datetime.utcnow().isoformat()
        self._save_agent_to_db(agent)
        return {"status": "paused"}
    
    def resume_agent(self, agent_id):
        agent = self.agents.get(agent_id)
        if not agent:
            return {"error": "Not found"}, 404
        agent.status = AgentStatus.RUNNING.value
        agent.updated_at = datetime.utcnow().isoformat()
        self._save_agent_to_db(agent)
        return {"status": "resumed"}
    
    def stop_agent(self, agent_id):
        agent = self.agents.get(agent_id)
        if not agent:
            return {"error": "Not found"}, 404
        if agent_id in self.stop_events:
            self.stop_events[agent_id].set()
        agent.status = AgentStatus.STOPPED.value
        agent.updated_at = datetime.utcnow().isoformat()
        self._save_agent_to_db(agent)
        return {"status": "stopped"}
    
    def delete_agent(self, agent_id):
        if agent_id in self.agents:
            del self.agents[agent_id]
        # Remove from database
        if self.db:
            try:
                with self.db._get_conn() as conn:
                    c = conn.cursor()
                    c.execute("DELETE FROM agents WHERE id = ?", (agent_id,))
                    conn.commit()
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Could not delete agent from DB: {e}")
        return {"status": "deleted"}
    
    def get_agent_status(self, agent_id):
        agent = self.agents.get(agent_id)
        if not agent:
            return {"error": "Not found"}, 404
        return {"id": agent.id, "name": agent.name, "status": agent.status, "model": agent.model}

_runtime = None
def get_agent_runtime(db=None):
    global _runtime
    if _runtime is None:
        _runtime = AgentRuntime(db=db)
    elif db is not None and _runtime.db is None:
        # Allow setting db after initialization
        _runtime.db = db
        _runtime._load_agents_from_db()
    return _runtime
