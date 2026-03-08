"""
TaskSpoke - A Spoke Adapter that models a directed task graph.

The agent navigates a DAG of tasks with dependencies, choosing which
task to start, complete, or skip at each cycle step.
"""
from typing import Dict, Any, List, Optional
from ..spoke_adapter import SpokeAdapter


# ── Default task graph ──────────────────────────────────────────────
DEFAULT_TASKS = {
    "research": {
        "deps": [],
        "effort": 2,
        "description": "Research requirements and prior art",
    },
    "design": {
        "deps": ["research"],
        "effort": 3,
        "description": "Design system architecture and interfaces",
    },
    "implement": {
        "deps": ["design"],
        "effort": 5,
        "description": "Write the implementation code",
    },
    "test": {
        "deps": ["implement"],
        "effort": 3,
        "description": "Write and run verification tests",
    },
    "deploy": {
        "deps": ["test"],
        "effort": 1,
        "description": "Deploy artefacts to production",
    },
}


class TaskSpoke(SpokeAdapter):
    """
    Spoke that exposes a directed task graph as an environment.

    State includes the current position in the graph, completion
    status of each node, and which actions are currently available.
    """

    # ── Status constants ────────────────────────────────────────────
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"

    def __init__(self, tasks: Optional[Dict[str, dict]] = None):
        self.tasks = tasks or dict(DEFAULT_TASKS)
        self.status: Dict[str, str] = {
            name: self.PENDING for name in self.tasks
        }
        self.current_task: Optional[str] = None
        self.cycle_count = 0
        self.work_remaining: Dict[str, int] = {
            name: info["effort"] for name, info in self.tasks.items()
        }
        self.decision_log: List[Dict[str, Any]] = []

    # ── SpokeAdapter interface ──────────────────────────────────────

    def observe(self) -> Dict[str, Any]:
        """Return observable state of the task graph."""
        self.cycle_count += 1
        available = self._available_tasks()
        completed = [t for t, s in self.status.items() if s == self.COMPLETED]
        blocked = [t for t, s in self.status.items()
                   if s == self.PENDING and t not in available]

        return {
            "current_task": self.current_task,
            "task_status": dict(self.status),
            "available_actions": self._available_actions(),
            "available_tasks": available,
            "completed_tasks": completed,
            "blocked_tasks": blocked,
            "completion_pct": len(completed) / len(self.tasks) * 100,
            "cycle": self.cycle_count,
            "work_remaining": dict(self.work_remaining),
            # Numerical features for voxelization
            "position": {
                "x": len(completed) * 100,
                "y": self.cycle_count * 10,
            },
            "state_hash": self._state_hash(),
        }

    def act(self, token: Dict[str, Any]) -> bool:
        """Execute an action token."""
        action = token.get("action", "")
        params = token.get("params", {})

        self.decision_log.append({
            "cycle": self.cycle_count,
            "action": action,
            "params": params,
        })

        if action == "start_task":
            return self._start_task(params.get("task_name", ""))
        elif action == "work_on_task":
            return self._work_on_task()
        elif action == "complete_task":
            return self._complete_task()
        elif action == "skip_task":
            return self._skip_task(params.get("task_name", ""))
        elif action == "navigate_to":
            return self._navigate_to(params.get("task_name", ""))
        elif action == "explore":
            # No-op but valid — agent is surveying
            return True

        return False

    def get_state_schema(self) -> Dict[str, Any]:
        """Return schema describing the state structure."""
        return {
            "current_task": {"type": "str", "nullable": True},
            "task_status": {"type": "dict", "values": "str"},
            "available_actions": {"type": "list", "items": "str"},
            "available_tasks": {"type": "list", "items": "str"},
            "completed_tasks": {"type": "list", "items": "str"},
            "blocked_tasks": {"type": "list", "items": "str"},
            "completion_pct": {"type": "float"},
            "cycle": {"type": "int"},
            "work_remaining": {"type": "dict", "values": "int"},
        }

    def get_name(self) -> str:
        return "TaskSpoke"

    # ── Helpers ─────────────────────────────────────────────────────

    def is_all_done(self) -> bool:
        """True when every non-skipped task is completed."""
        return all(
            s in (self.COMPLETED, self.SKIPPED) for s in self.status.values()
        )

    def _available_tasks(self) -> List[str]:
        """Tasks whose deps are all completed/skipped and are not done."""
        available = []
        for name, info in self.tasks.items():
            if self.status[name] in (self.COMPLETED, self.SKIPPED):
                continue
            deps_met = all(
                self.status[d] in (self.COMPLETED, self.SKIPPED)
                for d in info["deps"]
            )
            if deps_met:
                available.append(name)
        return available

    def _available_actions(self) -> List[str]:
        """Actions that are valid right now."""
        actions = ["explore"]
        available = self._available_tasks()

        if self.current_task:
            actions.append("work_on_task")
            if self.work_remaining.get(self.current_task, 0) <= 0:
                actions.append("complete_task")

        for t in available:
            if t != self.current_task:
                actions.append(f"start_task({t})")
                actions.append(f"navigate_to({t})")

        return actions

    def _start_task(self, task_name: str) -> bool:
        if task_name not in self.tasks:
            return False
        if task_name not in self._available_tasks():
            return False  # deps not met
        self.current_task = task_name
        self.status[task_name] = self.IN_PROGRESS
        print(f"  [TASK] Started: {task_name}")
        return True

    def _work_on_task(self) -> bool:
        if not self.current_task:
            return False
        remaining = self.work_remaining.get(self.current_task, 0)
        if remaining > 0:
            self.work_remaining[self.current_task] = remaining - 1
            left = self.work_remaining[self.current_task]
            print(f"  [TASK] Working on {self.current_task} "
                  f"({left} effort remaining)")
        return True

    def _complete_task(self) -> bool:
        if not self.current_task:
            return False
        if self.work_remaining.get(self.current_task, 0) > 0:
            return False  # still has effort remaining
        self.status[self.current_task] = self.COMPLETED
        print(f"  [TASK] Completed: {self.current_task}")
        self.current_task = None
        return True

    def _skip_task(self, task_name: str) -> bool:
        if task_name not in self.tasks:
            return False
        self.status[task_name] = self.SKIPPED
        if self.current_task == task_name:
            self.current_task = None
        print(f"  [TASK] Skipped: {task_name}")
        return True

    def _navigate_to(self, task_name: str) -> bool:
        if task_name not in self._available_tasks():
            return False
        self.current_task = task_name
        if self.status[task_name] == self.PENDING:
            self.status[task_name] = self.IN_PROGRESS
        print(f"  [TASK] Navigated to: {task_name}")
        return True

    def _state_hash(self) -> str:
        """Deterministic hash of the current state."""
        parts = []
        for name in sorted(self.status):
            parts.append(f"{name}={self.status[name]}")
        parts.append(f"cur={self.current_task}")
        return "|".join(parts)
