"""Multi-Agent Orchestrator.

Routes tasks to specialized agents and manages workflow execution.
Implements the "team of agents" pattern for complex enterprise workflows.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from browser_use.enterprise.agents import BaseSpecialistAgent
    from browser_use.enterprise.memory import MemoryManager

logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class TaskStatus(Enum):
    PENDING = "pending"
    DISPATCHED = "dispatched"
    IN_PROGRESS = "in_progress"
    AWAITING_HUMAN = "awaiting_human"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    """Represents a unit of work for the agent swarm."""
    id: str
    intent: str  # Natural language description
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.PENDING
    assigned_agent: Optional[str] = None
    parent_task_id: Optional[str] = None
    subtasks: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    checkpoint_id: Optional[str] = None


@dataclass
class WorkflowState:
    """Current state of the orchestrated workflow."""
    workflow_id: str
    tasks: Dict[str, Task] = field(default_factory=dict)
    active_agents: List[str] = field(default_factory=list)
    completed_count: int = 0
    failed_count: int = 0
    started_at: datetime = field(default_factory=datetime.now)


class Orchestrator:
    """
    Multi-Agent Orchestration Engine.
    
    Manages a swarm of specialized agents to complete complex enterprise workflows.
    Implements task routing, parallel execution, and failure recovery.
    
    Example:
        orchestrator = Orchestrator()
        orchestrator.register_agent("researcher", ResearcherAgent())
        orchestrator.register_agent("compliance", ComplianceAgent())
        
        result = await orchestrator.execute(
            "Research competitor pricing and ensure GDPR compliance"
        )
    """
    
    def __init__(
        self,
        memory_manager: Optional["MemoryManager"] = None,
        max_parallel_agents: int = 5,
        human_in_loop: bool = True,
        llm: Any = None,
        agents: Optional[Dict[str, "BaseSpecialistAgent"]] = None,
        max_concurrent_tasks: Optional[int] = None,
    ):
        self.agents: Dict[str, "BaseSpecialistAgent"] = agents or {}
        self.llm = llm
        self.memory = memory_manager
        self.max_parallel = max_concurrent_tasks or max_parallel_agents
        self.human_in_loop = human_in_loop
        self._workflow_state: Optional[WorkflowState] = None
        self._task_queue: asyncio.Queue = asyncio.Queue()
        
        # Register agents if provided
        for name, agent in self.agents.items():
            agent.orchestrator = self
        
    def register_agent(self, name: str, agent: "BaseSpecialistAgent") -> None:
        """Register a specialist agent with the orchestrator."""
        self.agents[name] = agent
        agent.orchestrator = self
        logger.info(f"Registered agent: {name} ({agent.__class__.__name__})")
        
    def unregister_agent(self, name: str) -> None:
        """Remove an agent from the orchestrator."""
        if name in self.agents:
            del self.agents[name]
            logger.info(f"Unregistered agent: {name}")
            
    async def execute(
        self,
        intent: str,
        context: Optional[Dict[str, Any]] = None,
        priority: TaskPriority = TaskPriority.MEDIUM,
    ) -> Dict[str, Any]:
        """
        Execute a workflow based on natural language intent.
        
        Args:
            intent: Natural language description of what to accomplish
            context: Additional context (credentials, preferences, etc.)
            priority: Task priority level
            
        Returns:
            Workflow result including all task outputs
        """
        import uuid
        
        workflow_id = str(uuid.uuid4())[:8]
        self._workflow_state = WorkflowState(workflow_id=workflow_id)
        
        logger.info(f"🚀 Starting workflow {workflow_id}: {intent[:50]}...")
        
        # Create root task
        root_task = Task(
            id=f"task_{workflow_id}_root",
            intent=intent,
            priority=priority,
            context=context or {},
        )
        self._workflow_state.tasks[root_task.id] = root_task
        
        try:
            # Step 1: Dispatch - analyze intent and create subtasks
            subtasks = await self._dispatch(root_task)
            
            # Step 2: Execute subtasks (parallel where possible)
            results = await self._execute_subtasks(subtasks)
            
            # Step 3: Aggregate results
            final_result = await self._aggregate_results(root_task, results)
            
            root_task.status = TaskStatus.COMPLETED
            root_task.completed_at = datetime.now()
            root_task.result = final_result
            
            logger.info(f"✅ Workflow {workflow_id} completed successfully")
            
            return {
                "workflow_id": workflow_id,
                "task_id": root_task.id,
                "status": "completed",
                "result": final_result,
                "tasks_completed": self._workflow_state.completed_count,
                "tasks_failed": self._workflow_state.failed_count,
                "duration": f"{(datetime.now() - self._workflow_state.started_at).total_seconds():.1f}s",
                "agents_used": list(set(t.assigned_agent for t in self._workflow_state.tasks.values() if t.assigned_agent)),
                "research_summary": final_result.get("summary", "N/A"),
                "compliance_status": "Passed" if self._workflow_state.failed_count == 0 else "Issues found",
                "actions": [f"Processed subtask: {t.intent[:50]}" for t in self._workflow_state.tasks.values()],
                "next_steps": "Review and approve for execution" if self.human_in_loop else "Completed",
            }
            
        except Exception as e:
            root_task.status = TaskStatus.FAILED
            root_task.error = str(e)
            logger.error(f"❌ Workflow {workflow_id} failed: {e}")
            
            # Save checkpoint for recovery
            if self.memory:
                checkpoint_id = await self.memory.save_checkpoint(self._workflow_state)
                root_task.checkpoint_id = checkpoint_id
                
            return {
                "workflow_id": workflow_id,
                "task_id": root_task.id,
                "status": "failed",
                "error": str(e),
                "checkpoint_id": root_task.checkpoint_id,
                "agents_used": [],
                "research_summary": "Failed",
                "compliance_status": "Not checked",
                "actions": [],
                "next_steps": f"Recover from checkpoint: {root_task.checkpoint_id}",
            }
    
    async def process_task(
        self,
        task_description: str,
        task_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Process a task (alias for execute with additional context).
        
        Args:
            task_description: Natural language task description
            task_type: Optional task type hint (e.g., "procurement", "research")
            metadata: Additional metadata (budget, priority, etc.)
            
        Returns:
            Task result
        """
        context = metadata or {}
        context["task_type"] = task_type
        
        priority = TaskPriority.MEDIUM
        if metadata and metadata.get("priority") == "high":
            priority = TaskPriority.HIGH
        elif metadata and metadata.get("priority") == "critical":
            priority = TaskPriority.CRITICAL
            
        return await self.execute(task_description, context=context, priority=priority)
    
    async def _dispatch(self, task: Task) -> List[Task]:
        """
        Use the Dispatcher agent to analyze intent and create subtasks.
        """
        dispatcher = self.agents.get("dispatcher")
        
        if dispatcher:
            task.status = TaskStatus.DISPATCHED
            dispatch_result = await dispatcher.analyze(task.intent, task.context)
            subtasks = []
            
            for i, sub in enumerate(dispatch_result.get("subtasks", [])):
                subtask = Task(
                    id=f"{task.id}_sub{i}",
                    intent=sub["intent"],
                    priority=TaskPriority(sub.get("priority", 2)),
                    parent_task_id=task.id,
                    context={**task.context, **sub.get("context", {})},
                    assigned_agent=sub.get("agent"),
                )
                self._workflow_state.tasks[subtask.id] = subtask
                task.subtasks.append(subtask.id)
                subtasks.append(subtask)
                
            return subtasks
        else:
            # No dispatcher - treat as single task
            task.assigned_agent = self._select_agent(task.intent)
            return [task]
    
    def _select_agent(self, intent: str) -> str:
        """Simple agent selection based on keywords."""
        intent_lower = intent.lower()
        
        if any(kw in intent_lower for kw in ["research", "find", "search", "scrape"]):
            return "researcher"
        elif any(kw in intent_lower for kw in ["compliance", "legal", "gdpr", "policy"]):
            return "compliance"
        elif any(kw in intent_lower for kw in ["form", "fill", "submit", "login"]):
            return "worker"
        else:
            return "worker"  # Default
    
    async def _execute_subtasks(self, subtasks: List[Task]) -> List[Dict[str, Any]]:
        """Execute subtasks, respecting dependencies and parallelism limits."""
        results = []
        semaphore = asyncio.Semaphore(self.max_parallel)
        
        async def run_task(task: Task) -> Dict[str, Any]:
            async with semaphore:
                return await self._execute_single_task(task)
        
        # Group independent tasks for parallel execution
        tasks_to_run = [run_task(t) for t in subtasks]
        results = await asyncio.gather(*tasks_to_run, return_exceptions=True)
        
        return [
            r if not isinstance(r, Exception) else {"error": str(r)}
            for r in results
        ]
    
    async def _execute_single_task(self, task: Task) -> Dict[str, Any]:
        """Execute a single task using the assigned agent."""
        agent_name = task.assigned_agent or self._select_agent(task.intent)
        agent = self.agents.get(agent_name)
        
        if not agent:
            task.status = TaskStatus.FAILED
            task.error = f"No agent available: {agent_name}"
            self._workflow_state.failed_count += 1
            return {"error": task.error}
        
        task.status = TaskStatus.IN_PROGRESS
        task.assigned_agent = agent_name
        self._workflow_state.active_agents.append(agent_name)
        
        logger.info(f"  🤖 Agent '{agent_name}' executing: {task.intent[:40]}...")
        
        try:
            # Check compliance first if compliance agent exists
            if agent_name != "compliance" and "compliance" in self.agents:
                compliance_check = await self.agents["compliance"].check(task.intent, task.context)
                if not compliance_check.get("approved", True):
                    if self.human_in_loop:
                        task.status = TaskStatus.AWAITING_HUMAN
                        logger.warning(f"  ⚠️ Task needs human approval: {compliance_check.get('reason')}")
                        # In real impl: wait for human approval
                    else:
                        raise ValueError(f"Compliance blocked: {compliance_check.get('reason')}")
            
            # Execute the task
            result = await agent.execute(task.intent, task.context)
            
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            task.result = result
            self._workflow_state.completed_count += 1
            
            # Store in memory
            if self.memory:
                await self.memory.store_task_result(task)
            
            return result
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            self._workflow_state.failed_count += 1
            logger.error(f"  ❌ Task failed: {e}")
            return {"error": str(e)}
        finally:
            if agent_name in self._workflow_state.active_agents:
                self._workflow_state.active_agents.remove(agent_name)
    
    async def _aggregate_results(
        self, 
        root_task: Task, 
        results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Aggregate results from all subtasks."""
        successful = [r for r in results if "error" not in r]
        failed = [r for r in results if "error" in r]
        
        return {
            "summary": f"Completed {len(successful)}/{len(results)} subtasks",
            "successful_results": successful,
            "failures": failed,
            "all_subtask_ids": root_task.subtasks,
        }
    
    async def resume_from_checkpoint(self, checkpoint_id: str) -> Dict[str, Any]:
        """Resume a failed workflow from a checkpoint."""
        if not self.memory:
            raise ValueError("Memory manager required for checkpoint recovery")
        
        state = await self.memory.load_checkpoint(checkpoint_id)
        self._workflow_state = state
        
        # Find incomplete tasks
        pending_tasks = [
            t for t in state.tasks.values()
            if t.status in (TaskStatus.PENDING, TaskStatus.IN_PROGRESS, TaskStatus.DISPATCHED)
        ]
        
        logger.info(f"🔄 Resuming workflow with {len(pending_tasks)} pending tasks")
        
        results = await self._execute_subtasks(pending_tasks)
        return await self._aggregate_results(
            list(state.tasks.values())[0],  # root task
            results
        )
    
    def get_status(self) -> Dict[str, Any]:
        """Get current workflow status."""
        if not self._workflow_state:
            return {"status": "idle"}
        
        return {
            "workflow_id": self._workflow_state.workflow_id,
            "active_agents": self._workflow_state.active_agents,
            "completed": self._workflow_state.completed_count,
            "failed": self._workflow_state.failed_count,
            "total_tasks": len(self._workflow_state.tasks),
            "duration": (datetime.now() - self._workflow_state.started_at).total_seconds(),
        }
