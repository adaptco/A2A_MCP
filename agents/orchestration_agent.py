# agents/orchestration_agent.py
from __future__ import annotations

import uuid
from typing import List

# Fix #2: Import for non-blocking I/O
from anyio import to_thread

from schemas.agent_artifacts import MCPArtifact
from schemas.project_plan import PlanAction, ProjectPlan
from orchestrator.storage import DBManager

AGENT_PIPELINE = [
    "ManagingAgent",
    "ArchitectureAgent",
    "CoderAgent",
    "TesterAgent",
]

class OrchestrationAgent:
    """Produces a typed blueprint that maps tasks to the agent pipeline."""

    AGENT_NAME = "OrchestrationAgent-Alpha"
    VERSION = "1.0.0"

    def __init__(self) -> None:
        self.db = DBManager()

    async def build_blueprint(
        self,
        project_name: str,
        task_descriptions: List[str],
        requester: str = "system",
    ) -> ProjectPlan:
        """Create project plan with non-blocking persistence."""
        actions: List[PlanAction] = []
        for desc in task_descriptions:
            for agent_name in AGENT_PIPELINE:
                actions.append(
                    PlanAction(
                        action_id=f"bp-{uuid.uuid4().hex[:8]}",
                        title=f"{agent_name}: {desc[:40]}",
                        instruction=desc,
                        metadata={"delegated_to": agent_name},
                    )
                )

        plan = ProjectPlan(
            plan_id=f"blueprint-{uuid.uuid4().hex[:8]}",
            project_name=project_name,
            requester=requester,
            actions=actions,
        )

        # Fix #1: Handle Pydantic v1 vs v2 API difference
        if hasattr(plan, 'model_dump_json'):
            plan_json = plan.model_dump_json()  # Pydantic v2
        else:
            plan_json = plan.json()  # Pydantic v1 fallback

        artifact = MCPArtifact(
            artifact_id=f"bp-art-{uuid.uuid4().hex[:8]}",
            type="blueprint",
            content=plan_json,
            metadata={"agent": self.AGENT_NAME},
        )

        # Fix #2: Wrap synchronous DB call in threadpool
        await to_thread.run_sync(self.db.save_artifact, artifact)

        return plan
