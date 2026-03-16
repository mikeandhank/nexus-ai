"""
Agent Trigger Chains - Multi-Agent Orchestration
===============================================
Allows agents to trigger other agents based on conditions.
This is the core OS functionality for agent orchestration.
"""

import os
import json
import uuid
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

logging.basicConfig(level=logging.INFO__)
logger = logging.getLogger(__name__)


class TriggerType(Enum):
    """Types of triggers that can start an agent"""
    MANUAL = "manual"           # User triggers manually
    MESSAGE = "message"         # When agent receives a message
    COMPLETION = "completion"  # When another agent completes
    SCHEDULE = "schedule"       # On a cron schedule
    CONDITION = "condition"    # When a condition is met
    WEBHOOK = "webhook"        # External HTTP trigger


class ChainState(Enum):
    """State of a trigger chain"""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    WAITING = "waiting"


@dataclass
class Trigger:
    """A trigger definition"""
    trigger_id: str
    agent_id: str
    trigger_type: TriggerType
    config: Dict = field(default_factory=dict)
    enabled: bool = True
    
    # For CONDITION triggers
    condition: str = ""
    condition_check_interval: int = 60  # seconds
    
    # For SCHEDULE triggers
    cron_expression: str = ""
    
    # For COMPLETION triggers  
    source_agent_id: str = ""


@dataclass
class ChainExecution:
    """An execution of a trigger chain"""
    execution_id: str
    chain_id: str
    state: ChainState
    started_at: datetime
    completed_at: Optional[datetime] = None
    results: List[Dict] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    context: Dict = field(default_factory=dict)


class AgentTriggerChain:
    """
    Multi-Agent Trigger Chains
    
    Enables:
    - Agent A triggers Agent B when complete
    - Conditional agent starts
    - Scheduled agent runs
    - Webhook-triggered agents
    - Chained workflows (A → B → C)
    """
    
    def __init__(self, kernel=None):
        self.kernel = kernel
        self.triggers: Dict[str, Trigger] = {}
        self.chains: Dict[str, List[Trigger]] = {}  # chain_id -> [triggers]
        self.executions: Dict[str, ChainExecution] = {}
        
    def create_trigger(self, agent_id: str, trigger_type: TriggerType, 
                     config: Dict = None, condition: str = "",
                     cron: str = "", source_agent: str = "") -> Trigger:
        """Create a new trigger for an agent"""
        trigger_id = f"trigger_{uuid.uuid4().hex[:12]}"
        
        trigger = Trigger(
            trigger_id=trigger_id,
            agent_id=agent_id,
            trigger_type=trigger_type,
            config=config or {},
            condition=condition,
            cron_expression=cron,
            source_agent_id=source_agent
        )
        
        self.triggers[trigger_id] = trigger
        
        logger.info(f"Created trigger {trigger_id} for agent {agent_id}, type {trigger_type.value}")
        return trigger
    
    def create_chain(self, name: str, triggers: List[Trigger]) -> str:
        """Create a chain of triggers"""
        chain_id = f"chain_{uuid.uuid4().hex[:12]}"
        
        self.chains[chain_id] = triggers
        
        logger.info(f"Created chain {chain_id} with {len(triggers)} triggers")
        return chain_id
    
    def trigger(self, trigger_type: TriggerType, source_id: str = "",
               message: str = "", context: Dict = None) -> List[ChainExecution]:
        """
        Fire triggers based on event.
        
        Returns list of chain executions started.
        """
        context = context or {}
        executions = []
        
        for trigger_id, trigger in self.triggers.items():
            if not trigger.enabled:
                continue
                
            # Check if this trigger should fire
            should_fire = False
            
            if trigger_type == TriggerType.COMPLETION:
                should_fire = (trigger.source_agent_id == source_id)
                
            elif trigger_type == TriggerType.MESSAGE:
                should_fire = (trigger.trigger_type == TriggerType.MESSAGE)
                
            elif trigger_type == TriggerType.WEBHOOK:
                should_fire = (trigger.trigger_type == TriggerType.WEBHOOK)
                
            elif trigger_type == TriggerType.MANUAL:
                should_fire = (trigger.trigger_type == TriggerType.MANUAL)
            
            if should_fire:
                # Execute the trigger
                execution = self._execute_trigger(trigger, context)
                executions.append(execution)
        
        return executions
    
    def _execute_trigger(self, trigger: Trigger, context: Dict = None) -> ChainExecution:
        """Execute a single trigger"""
        context = context or {}
        
        execution_id = f"exec_{uuid.uuid4().hex[:12]}"
        
        execution = ChainExecution(
            execution_id=execution_id,
            chain_id=trigger.trigger_id,
            state=ChainState.RUNNING,
            started_at=datetime.utcnow(),
            context=context
        )
        
        self.executions[execution_id] = execution
        
        logger.info(f"Executing trigger {trigger.trigger_id} for agent {trigger.agent_id}")
        
        # Execute via kernel if available
        if self.kernel:
            try:
                # Start the agent
                result = self.kernel.start_agent(trigger.agent_id)
                execution.results.append({
                    "action": "start_agent",
                    "agent_id": trigger.agent_id,
                    "result": result
                })
                
                # Check if we need to chain to next
                if trigger.config.get("chain_next"):
                    next_agent = trigger.config["chain_next"]
                    next_trigger = self.create_trigger(
                        agent_id=next_agent,
                        trigger_type=TriggerType.COMPLETION,
                        source_agent=trigger.agent_id
                    )
                    execution.results.append({
                        "action": "chained_to",
                        "agent_id": next_agent
                    })
                
                execution.state = ChainState.COMPLETED
                
            except Exception as e:
                execution.state = ChainState.FAILED
                execution.errors.append(str(e))
                logger.error(f"Trigger execution failed: {e}")
        
        execution.completed_at = datetime.utcnow()
        
        return execution
    
    def get_trigger(self, trigger_id: str) -> Optional[Trigger]:
        """Get a trigger by ID"""
        return self.triggers.get(trigger_id)
    
    def get_agent_triggers(self, agent_id: str) -> List[Trigger]:
        """Get all triggers for an agent"""
        return [t for t in self.triggers.values() if t.agent_id == agent_id]
    
    def get_execution(self, execution_id: str) -> Optional[ChainExecution]:
        """Get execution details"""
        return self.executions.get(execution_id)
    
    def get_chain_executions(self, chain_id: str) -> List[ChainExecution]:
        """Get all executions for a chain"""
        return [e for e in self.executions.values() if e.chain_id == chain_id]
    
    def enable_trigger(self, trigger_id: str) -> bool:
        """Enable a trigger"""
        if trigger_id in self.triggers:
            self.triggers[trigger_id].enabled = True
            return True
        return False
    
    def disable_trigger(self, trigger_id: str) -> bool:
        """Disable a trigger"""
        if trigger_id in self.triggers:
            self.triggers[trigger_id].enabled = False
            return True
        return False
    
    def delete_trigger(self, trigger_id: str) -> bool:
        """Delete a trigger"""
        if trigger_id in self.triggers:
            del self.triggers[trigger_id]
            return True
        return False
    
    def list_triggers(self, agent_id: str = None) -> List[Dict]:
        """List all triggers"""
        triggers = self.triggers.values()
        
        if agent_id:
            triggers = [t for t in triggers if t.agent_id == agent_id]
        
        return [
            {
                "trigger_id": t.trigger_id,
                "agent_id": t.agent_id,
                "type": t.trigger_type.value,
                "enabled": t.enabled,
                "config": t.config
            }
            for t in triggers
        ]
    
    def get_stats(self) -> Dict:
        """Get trigger chain statistics"""
        return {
            "total_triggers": len(self.triggers),
            "total_chains": len(self.chains),
            "total_executions": len(self.executions),
            "by_type": {
                t.value: sum(1 for tr in self.triggers.values() if tr.trigger_type == t)
                for t in TriggerType
            },
            "execution_states": {
                s.value: sum(1 for e in self.executions.values() if e.state == s)
                for s in ChainState
            }
        }


# Examples:
# 
# 1. Agent B triggers when Agent A completes
#    trigger = chain.trigger(TriggerType.COMPLETION, source_id="agent_A")
#
# 2. Create a chain: A → B → C
#    chain.create_chain("workflow", [trigger_A, trigger_B, trigger_C])
#
# 3. Scheduled agent
#    trigger = chain.create_trigger(
#        agent_id="daily_report_agent",
#        trigger_type=TriggerType.SCHEDULE,
#        cron="0 9 * * *"  # 9 AM daily
#    )
#
# 4. Conditional trigger
#    trigger = chain.create_trigger(
#        agent_id="escalation_agent",
#        trigger_type=TriggerType.CONDITION,
#        condition="urgency > 7"
#    )

# Singleton
_chain = None

def get_trigger_chain(kernel=None) -> AgentTriggerChain:
    global _chain
    if _chain is None:
        _chain = AgentTriggerChain(kernel)
    return _chain
