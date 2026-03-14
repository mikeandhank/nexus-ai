"""
NexusOS v2 - Multi-Agent Orchestration

Manages multiple agents per user with:
- Agent creation/deletion
- Role-based agents
- Shared memory
- Tool allocation
- Status tracking
"""

import os
import json
import uuid
import threading
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from enum import Enum
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    IDLE = "idle"
    THINKING = "thinking"
    ACTING = "acting"
    WAITING = "waiting"
    ERROR = "error"


class Agent:
    """
    Represents an AI agent in NexusOS.
    
    Each agent has:
    - Unique ID
    - Name and role
    - Personality configuration
    - Allocated tools
    - Memory space
    - Status
    """
    
    def __init__(self, agent_id: str, user_id: str, name: str, role: str = None,
                 personality: Dict = None, tools: List[str] = None):
        self.id = agent_id
        self.user_id = user_id
        self.name = name
        self.role = role or "general"
        self.personality = personality or {}
        self.tools = tools or []
        self.status = AgentStatus.IDLE
        self.created_at = datetime.now().isoformat()
        self.last_active = self.created_at
        self.conversation_history = []
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "role": self.role,
            "personality": self.personality,
            "tools": self.tools,
            "status": self.status.value,
            "created_at": self.created_at,
            "last_active": self.last_active,
        }
    
    def update_status(self, status: AgentStatus):
        """Update agent status."""
        self.status = status
        self.last_active = datetime.now().isoformat()


class AgentPool:
    """
    Manages multiple agents per user.
    
    Features:
    - Create/delete agents
    - Assign roles and tools
    - Shared memory space
    - Concurrent execution
    - Status tracking
    """
    
    def __init__(self, db=None, tool_engine=None):
        self.db = db
        self.tool_engine = tool_engine
        self.agents: Dict[str, Agent] = {}
        self.active_agents: Dict[str, threading.Thread] = {}
        
        # Default agent templates
        self.templates = {
            "general": {
                "role": "General assistant",
                "personality": {"tone": "helpful", "verbosity": "balanced"},
                "tools": ["file_read", "file_list", "http_get"]
            },
            "researcher": {
                "role": "Research specialist",
                "personality": {"tone": "analytical", "verbosity": "detailed"},
                "tools": ["search_files", "http_get", "http_post"]
            },
            "coder": {
                "role": "Code assistant",
                "personality": {"tone": "precise", "verbosity": "concise"},
                "tools": ["file_read", "file_write", "shell_command", "process_run"]
            },
            "analyst": {
                "role": "Data analyst",
                "personality": {"tone": "analytical", "verbosity": "detailed"},
                "tools": ["file_read", "file_list", "search_files"]
            },
            "manager": {
                "role": "Project manager",
                "personality": {"tone": "direct", "verbosity": "brief"},
                "tools": ["file_list", "file_mkdir", "http_get"]
            }
        }
        
        logger.info("AgentPool initialized")
    
    def create_agent(self, user_id: str, name: str, template: str = "general", 
                    **kwargs) -> Agent:
        """Create a new agent."""
        agent_id = uuid.uuid4().hex
        
        # Get template or use custom
        if template in self.templates:
            tmpl = self.templates[template].copy()
        else:
            tmpl = {"role": template, "personality": {}, "tools": []}
        
        tmpl.update(kwargs)
        
        agent = Agent(
            agent_id=agent_id,
            user_id=user_id,
            name=name,
            role=tmpl.get("role"),
            personality=tmpl.get("personality", {}),
            tools=tmpl.get("tools", [])
        )
        
        # Save to database if available
        if self.db:
            self.db.create_agent(user_id, name, role=agent.role, 
                               personality=json.dumps(agent.personality),
                               tools=json.dumps(agent.tools))
        
        self.agents[agent_id] = agent
        logger.info(f"Created agent: {name} ({agent_id})")
        
        return agent
    
    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get agent by ID."""
        return self.agents.get(agent_id)
    
    def get_agents(self, user_id: str = None) -> List[Agent]:
        """Get all agents, optionally filtered by user."""
        if user_id:
            return [a for a in self.agents.values() if a.user_id == user_id]
        return list(self.agents.values())
    
    def delete_agent(self, agent_id: str) -> bool:
        """Delete an agent."""
        if agent_id in self.agents:
            agent = self.agents[agent_id]
            del self.agents[agent_id]
            logger.info(f"Deleted agent: {agent.name}")
            return True
        return False
    
    def update_agent(self, agent_id: str, **kwargs) -> Optional[Agent]:
        """Update agent properties."""
        agent = self.agents.get(agent_id)
        if not agent:
            return None
        
        if 'name' in kwargs:
            agent.name = kwargs['name']
        if 'role' in kwargs:
            agent.role = kwargs['role']
        if 'personality' in kwargs:
            agent.personality = kwargs['personality']
        if 'tools' in kwargs:
            agent.tools = kwargs['tools']
        
        agent.last_active = datetime.now().isoformat()
        
        # Save to database
        if self.db:
            self.db.update_agent(agent_id, **kwargs)
        
        return agent
    
    def assign_tools(self, agent_id: str, tools: List[str]) -> Agent:
        """Assign tools to an agent."""
        agent = self.agents.get(agent_id)
        if agent:
            agent.tools = tools
            if self.db:
                self.db.update_agent(agent_id, tools=json.dumps(tools))
        return agent
    
    def get_available_templates(self) -> Dict:
        """Get available agent templates."""
        return self.templates.copy()
    
    def execute_task(self, agent_id: str, task: str, context: Dict = None) -> Dict:
        """Execute a task with an agent."""
        agent = self.agents.get(agent_id)
        if not agent:
            return {"error": f"Agent {agent_id} not found"}
        
        agent.update_status(AgentStatus.THINKING)
        
        try:
            # Build system prompt from personality
            system_prompt = self._build_system_prompt(agent)
            
            # Execute with tools if available
            if agent.tools and self.tool_engine:
                # Agent would use tools here
                pass
            
            agent.update_status(AgentStatus.ACTING)
            
            # Simulate response (actual LLM call would go here)
            response = f"[{agent.name}] Processing: {task}"
            
            agent.update_status(AgentStatus.IDLE)
            
            return {
                "agent_id": agent_id,
                "agent_name": agent.name,
                "response": response,
                "status": agent.status.value
            }
            
        except Exception as e:
            agent.update_status(AgentStatus.ERROR)
            return {"error": str(e)}
    
    def _build_system_prompt(self, agent: Agent) -> str:
        """Build system prompt from agent personality."""
        parts = [f"You are {agent.name}, a {agent.role}."]
        
        personality = agent.personality
        if 'tone' in personality:
            parts.append(f"Tone: {personality['tone']}.")
        if 'verbosity' in personality:
            parts.append(f"Verbosity: {personality['verbosity']}.")
        
        return " ".join(parts)
    
    def get_status(self) -> Dict:
        """Get pool status."""
        return {
            "total_agents": len(self.agents),
            "active_agents": len([a for a in self.agents.values() if a.status != AgentStatus.IDLE]),
            "by_status": {
                status.value: len([a for a in self.agents.values() if a.status == status])
                for status in AgentStatus
            }
        }


# Global instance
_agent_pool = None

def get_agent_pool(db=None, tool_engine=None) -> AgentPool:
    """Get agent pool singleton."""
    global _agent_pool
    if _agent_pool is None:
        _agent_pool = AgentPool(db, tool_engine)
    return _agent_pool
