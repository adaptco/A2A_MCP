"""
Swarm Runtime — Dependency-aware DAG orchestrator for multi-agent task swarms.
Ported from: sovereign-mcp/src/orchestration/runtime.py (RuntimeExecutorV2)
"""
import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("SwarmRuntime")


@dataclass
class AgentTask:
    """Declarative representation of a unit of work assigned to an agent."""
    agent_id: str
    action: str
    params: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    status: str = "PENDING"   # PENDING | RUNNING | COMPLETED | FAILED | SKIPPED
    result: Optional[Any] = None


class SwarmRuntime:
    """
    Orchestrates a directed acyclic graph (DAG) of AgentTasks.
    Resolves dependencies, executes agents concurrently, and emits
    lifecycle events to the AgenticRuntime (if provided).
    """

    def __init__(self, runtime=None):
        """
        Args:
            runtime: Optional AgenticRuntime for recording swarm telemetry.
        """
        self.runtime = runtime
        self.tasks: Dict[str, AgentTask] = {}
        self.observers: List[Callable[[str, Dict[str, Any]], None]] = []

    # ------------------------------------------------------------------
    # Observer pattern
    # ------------------------------------------------------------------

    def add_observer(self, observer: Callable[[str, Dict[str, Any]], None]):
        self.observers.append(observer)

    def _notify(self, event_type: str, data: Dict[str, Any]):
        for obs in self.observers:
            try:
                obs(event_type, data)
            except Exception as exc:
                logger.warning(f"SwarmRuntime: Observer error — {exc}")

    # ------------------------------------------------------------------
    # Task management
    # ------------------------------------------------------------------

    def register_task(self, task_id: str, task: AgentTask):
        self.tasks[task_id] = task

    async def run_task(self, task_id: str):
        task = self.tasks[task_id]

        # Wait on dependencies
        for dep_id in task.dependencies:
            while self.tasks[dep_id].status not in ("COMPLETED", "FAILED", "SKIPPED"):
                await asyncio.sleep(0.05)
            if self.tasks[dep_id].status in ("FAILED", "SKIPPED"):
                logger.warning(f"SwarmRuntime: Skipping [{task_id}] — dependency [{dep_id}] failed.")
                task.status = "SKIPPED"
                return

        task.status = "RUNNING"
        self._notify("TASK_START", {"task_id": task_id, "agent": task.agent_id})
        logger.info(f"SwarmRuntime: [{task_id}] started by agent [{task.agent_id}]")

        try:
            # If the agent is callable (BaseAgent subclass), execute it
            agent = task.params.pop("_agent_instance", None)
            if agent and hasattr(agent, "execute"):
                task.result = await agent.execute(task.action, task.params)
            else:
                # Stub: basic simulation of work
                await asyncio.sleep(0.1)
                task.result = {"output": f"Success from {task.agent_id}", "action": task.action}

            task.status = "COMPLETED"
            self._notify("TASK_COMPLETE", {"task_id": task_id, "status": "success", "result": task.result})
            logger.info(f"SwarmRuntime: [{task_id}] completed.")

        except Exception as exc:
            task.status = "FAILED"
            task.result = {"error": str(exc)}
            self._notify("TASK_COMPLETE", {"task_id": task_id, "status": "failed", "error": str(exc)})
            logger.error(f"SwarmRuntime: [{task_id}] failed — {exc}")

    # ------------------------------------------------------------------
    # Swarm spawning
    # ------------------------------------------------------------------

    async def spawn_swarm(self, tasks: Dict[str, AgentTask]) -> Dict[str, AgentTask]:
        """
        Register and execute all tasks concurrently, respecting their dependency graph.
        Returns the completed task registry.
        """
        for tid, task in tasks.items():
            self.register_task(tid, task)

        await asyncio.gather(*(self.run_task(tid) for tid in tasks))
        return self.tasks
