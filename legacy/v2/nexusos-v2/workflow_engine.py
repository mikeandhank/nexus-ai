"""
Workflow Engine - Agent Workflow Definitions
=============================================
Defines and executes multi-agent workflows.
"""

import os
import json
import uuid
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WorkflowState(Enum):
    """Workflow execution states"""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepType(Enum):
    """Types of workflow steps"""
    AGENT = "agent"           # Run an agent
    CONDITION = "condition"   # Branch based on condition
    WAIT = "wait"            # Wait for duration or event
    TRANSFORM = "transform"  # Transform data
    WEBHOOK = "webhook"      # Call external service
    APPROVAL = "approval"    # Wait for human approval


@dataclass
class WorkflowStep:
    """A single step in a workflow"""
    step_id: str
    step_type: StepType
    name: str
    config: Dict = field(default_factory=dict)
    
    # For AGENT steps
    agent_id: str = ""
    input_mapping: Dict = field(default_factory=dict)  # input -> source
    
    # For CONDITION steps
    condition: str = ""
    branches: Dict = field(default_factory=dict)  # "true" -> next_step, "false" -> next_step
    
    # For WAIT steps
    duration_seconds: int = 0
    wait_for_event: str = ""
    
    # For APPROVAL steps
    approver_email: str = ""


@dataclass
class Workflow:
    """A workflow definition"""
    workflow_id: str
    name: str
    description: str
    version: int = 1
    state: WorkflowState = WorkflowState.DRAFT
    steps: List[WorkflowStep] = field(default_factory=list)
    
    # Metadata
    created_by: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    # Execution
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    current_step: str = ""


@dataclass
class WorkflowExecution:
    """An instance of a workflow running"""
    execution_id: str
    workflow_id: str
    state: WorkflowState
    started_at: datetime
    completed_at: Optional[datetime] = None
    
    # Step tracking
    current_step_id: str = ""
    completed_steps: List[str] = field(default_factory=list)
    step_results: Dict = field(default_factory=dict)
    
    # Data context
    context: Dict = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)


class WorkflowEngine:
    """
    Workflow Engine for Multi-Agent Orchestration
    
    Features:
    - Visual workflow definitions
    - Conditional branching
    - Parallel execution paths
    - Human approval gates
    - Webhook integrations
    - Retry logic
    - Rollback support
    """
    
    def __init__(self, kernel=None):
        self.kernel = kernel
        self.workflows: Dict[str, Workflow] = {}
        self.executions: Dict[str, WorkflowExecution] = {}
    
    # ========== WORKFLOW MANAGEMENT ==========
    
    def create_workflow(self, name: str, description: str = "", 
                       created_by: str = "") -> Workflow:
        """Create a new workflow"""
        workflow_id = f"wf_{uuid.uuid4().hex[:12]}"
        
        workflow = Workflow(
            workflow_id=workflow_id,
            name=name,
            description=description,
            created_by=created_by
        )
        
        self.workflows[workflow_id] = workflow
        logger.info(f"Created workflow: {name} ({workflow_id})")
        
        return workflow
    
    def add_step(self, workflow_id: str, step: WorkflowStep) -> Dict:
        """Add a step to a workflow"""
        if workflow_id not in self.workflows:
            return {"success": False, "error": "Workflow not found"}
        
        workflow = self.workflows[workflow_id]
        workflow.steps.append(step)
        workflow.updated_at = datetime.utcnow()
        
        logger.info(f"Added step {step.name} to workflow {workflow_id}")
        
        return {"success": True, "step_id": step.step_id}
    
    def activate_workflow(self, workflow_id: str) -> Dict:
        """Activate a workflow for execution"""
        if workflow_id not in self.workflows:
            return {"success": False, "error": "Workflow not found"}
        
        workflow = self.workflows[workflow_id]
        
        # Validate workflow
        if not workflow.steps:
            return {"success": False, "error": "Workflow has no steps"}
        
        workflow.state = WorkflowState.ACTIVE
        workflow.updated_at = datetime.utcnow()
        
        return {"success": True, "workflow": workflow.workflow_id}
    
    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """Get a workflow"""
        return self.workflows.get(workflow_id)
    
    def list_workflows(self, state: WorkflowState = None) -> List[Dict]:
        """List workflows"""
        workflows = self.workflows.values()
        
        if state:
            workflows = [w for w in workflows if w.state == state]
        
        return [
            {
                "workflow_id": w.workflow_id,
                "name": w.name,
                "description": w.description,
                "state": w.state.value,
                "steps": len(w.steps),
                "created_by": w.created_by,
                "created_at": w.created_at.isoformat()
            }
            for w in workflows
        ]
    
    # ========== EXECUTION ==========
    
    def start_workflow(self, workflow_id: str, initial_context: Dict = None) -> WorkflowExecution:
        """Start executing a workflow"""
        
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        workflow = self.workflows[workflow_id]
        
        if workflow.state != WorkflowState.ACTIVE:
            raise ValueError(f"Workflow not active (state: {workflow.state.value})")
        
        execution_id = f"exec_{uuid.uuid4().hex[:12]}"
        
        execution = WorkflowExecution(
            execution_id=execution_id,
            workflow_id=workflow_id,
            state=WorkflowState.RUNNING,
            started_at=datetime.utcnow(),
            context=initial_context or {}
        )
        
        self.executions[execution_id] = execution
        workflow.started_at = datetime.utcnow()
        
        # Start first step
        if workflow.steps:
            execution.current_step_id = workflow.steps[0].step_id
            self._execute_step(execution, workflow.steps[0])
        
        return execution
    
    def _execute_step(self, execution: WorkflowExecution, step: WorkflowStep):
        """Execute a single workflow step"""
        
        try:
            result = None
            
            if step.step_type == StepType.AGENT:
                result = self._execute_agent_step(execution, step)
                
            elif step.step_type == StepType.CONDITION:
                result = self._execute_condition_step(execution, step)
                
            elif step.step_type == StepType.WAIT:
                result = self._execute_wait_step(execution, step)
                
            elif step.step_type == StepType.WEBHOOK:
                result = self._execute_webhook_step(execution, step)
                
            elif step.step_type == StepType.APPROVAL:
                result = self._execute_approval_step(execution, step)
            
            # Store result
            execution.step_results[step.step_id] = result
            
            # Mark step complete
            execution.completed_steps.append(step.step_id)
            
        except Exception as e:
            execution.errors.append(f"Step {step.step_id}: {str(e)}")
            execution.state = WorkflowState.FAILED
    
    def _execute_agent_step(self, execution: WorkflowExecution, step: WorkflowStep) -> Dict:
        """Execute an agent step"""
        
        # Map inputs
        input_data = {}
        for target, source in step.input_mapping.items():
            if source == "context":
                input_data[target] = execution.context.get(target)
            elif source.startswith("step."):
                step_id = source.split(".")[1]
                input_data[target] = execution.step_results.get(step_id)
        
        # Execute via kernel
        if self.kernel and step.agent_id:
            result = self.kernel.start_agent(step.agent_id, input_data)
            return {"agent_id": step.agent_id, "result": result}
        
        return {"status": "simulated", "input": input_data}
    
    def _execute_condition_step(self, execution: WorkflowExecution, step: WorkflowStep) -> Dict:
        """Execute a condition branch"""
        
        # Simple condition evaluation
        condition_result = True  # TODO: implement proper condition parser
        
        branch = "true" if condition_result else "false"
        
        return {
            "condition": step.condition,
            "branch": branch,
            "result": condition_result
        }
    
    def _execute_wait_step(self, execution: WorkflowExecution, step: WorkflowStep) -> Dict:
        """Execute a wait step"""
        
        return {
            "wait_type": "duration" if step.duration_seconds else "event",
            "duration": step.duration_seconds,
            "event": step.wait_for_event
        }
    
    def _execute_webhook_step(self, execution: WorkflowExecution, step: WorkflowStep) -> Dict:
        """Execute a webhook call"""
        
        import requests
        
        url = step.config.get("url", "")
        method = step.config.get("method", "POST")
        headers = step.config.get("headers", {})
        
        response = requests.request(method, url, json=execution.context, 
                                   headers=headers, timeout=30)
        
        return {
            "url": url,
            "status_code": response.status_code,
            "response": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text
        }
    
    def _execute_approval_step(self, execution: WorkflowExecution, step: WorkflowStep) -> Dict:
        """Execute an approval gate"""
        
        return {
            "approval_required": True,
            "approver": step.approver_email,
            "status": "pending"
        }
    
    def get_execution(self, execution_id: str) -> Optional[WorkflowExecution]:
        """Get execution details"""
        return self.executions.get(execution_id)
    
    def pause_workflow(self, execution_id: str) -> Dict:
        """Pause a running workflow"""
        if execution_id in self.executions:
            self.executions[execution_id].state = WorkflowState.PAUSED
            return {"success": True}
        return {"success": False, "error": "Execution not found"}
    
    def resume_workflow(self, execution_id: str) -> Dict:
        """Resume a paused workflow"""
        if execution_id in self.executions:
            self.executions[execution_id].state = WorkflowState.RUNNING
            return {"success": True}
        return {"success": False, "error": "Execution not found"}
    
    def cancel_workflow(self, execution_id: str) -> Dict:
        """Cancel a workflow execution"""
        if execution_id in self.executions:
            self.executions[execution_id].state = WorkflowState.CANCELLED
            self.executions[execution_id].completed_at = datetime.utcnow()
            return {"success": True}
        return {"success": False, "error": "Execution not found"}
    
    def get_stats(self) -> Dict:
        """Get workflow statistics"""
        return {
            "total_workflows": len(self.workflows),
            "active_workflows": sum(1 for w in self.workflows.values() if w.state == WorkflowState.ACTIVE),
            "total_executions": len(self.executions),
            "running": sum(1 for e in self.executions.values() if e.state == WorkflowState.RUNNING),
            "completed": sum(1 for e in self.executions.values() if e.state == WorkflowState.COMPLETED),
            "failed": sum(1 for e in self.executions.values() if e.state == WorkflowState.FAILED)
        }


# Example workflow builder
def create_data_pipeline(name: str) -> Workflow:
    """Create a data processing pipeline workflow"""
    from workflow_engine import WorkflowEngine, WorkflowStep, StepType
    
    engine = WorkflowEngine()
    
    workflow = engine.create_workflow(
        name=name,
        description="Extract → Transform → Load pipeline"
    )
    
    # Step 1: Extract
    step1 = WorkflowStep(
        step_id="extract",
        step_type=StepType.AGENT,
        name="Extract Data",
        agent_id="data_extractor",
        input_mapping={"query": "context"}
    )
    
    # Step 2: Transform
    step2 = WorkflowStep(
        step_id="transform",
        step_type=StepType.AGENT,
        name="Transform Data",
        agent_id="data_transformer",
        input_mapping={"data": "step.extract"}
    )
    
    # Step 3: Load
    step3 = WorkflowStep(
        step_id="load",
        step_type=StepType.AGENT,
        name="Load Data",
        agent_id="data_loader",
        input_mapping={"data": "step.transform"}
    )
    
    # Step 4: Notify
    step4 = WorkflowStep(
        step_id="notify",
        step_type=StepType.WEBHOOK,
        name="Notify Completion",
        config={"url": "https://hooks.example.com/notify", "method": "POST"}
    )
    
    engine.add_step(workflow.workflow_id, step1)
    engine.add_step(workflow.workflow_id, step2)
    engine.add_step(workflow.workflow_id, step3)
    engine.add_step(workflow.workflow_id, step4)
    
    engine.activate_workflow(workflow.workflow_id)
    
    return workflow


# Singleton
_workflow_engine = None

def get_workflow_engine(kernel=None) -> WorkflowEngine:
    global _workflow_engine
    if _workflow_engine is None:
        _workflow_engine = WorkflowEngine(kernel)
    return _workflow_engine
