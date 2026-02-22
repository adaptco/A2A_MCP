# A2A_MCP/agents/orchestration_agent.py
"""
OrchestrationAgent — Contract / blueprint director.

Defines the canonical execution order across the agent swarm and
produces a ProjectPlan artifact that downstream agents consume.
"""
from __future__ import annotations

from fastapi.concurrency import run_in_threadpool
import uuid
from typing import List

from fastapi.concurrency import run_in_threadpool

from schemas.agent_artifacts import MCPArtifact
from schemas.project_plan import PlanAction, ProjectPlan
from orchestrator.storage import DBManager


# The canonical delegation pipeline
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
        """
        Accept a list of high-level task descriptions and wrap them into a
        ProjectPlan with explicit agent-delegation metadata.
        """
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

        # Persist a blueprint artifact
        artifact = MCPArtifact(
            artifact_id=f"bp-art-{uuid.uuid4().hex[:8]}",
            type="blueprint",
            content=plan.model_dump_json(),
            metadata={"agent": self.AGENT_NAME},
        )
        await run_in_threadpool(self.db.save_artifact, artifact)
        return plan
