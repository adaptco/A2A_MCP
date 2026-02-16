# A2A_MCP/agents/architecture_agent.py
"""
ArchitectureAgent — System design mapper.

Given a ProjectPlan, produces architecture artifacts (component descriptions,
dependency graphs) and registers them in the PINN WorldModel as VectorTokens.
"""
from __future__ import annotations

import uuid
from typing import List

from agents.pinn_agent import PINNAgent
from orchestrator.storage import DBManager
from schemas.agent_artifacts import MCPArtifact
from schemas.project_plan import ProjectPlan
from schemas.world_model import VectorToken


class ArchitectureAgent:
    """Maps system architecture from a ProjectPlan using the System Expert Model."""

    AGENT_NAME = "ArchitectureAgent-Alpha"
    VERSION = "1.0.0"

    def __init__(self) -> None:
        self.pinn = PINNAgent()
        self.db = DBManager()

    async def map_system(self, plan: ProjectPlan) -> List[MCPArtifact]:
        """
        For each action in the plan, produce an architecture artifact and
        record it in the PINN WorldModel.

        Returns the list of architecture artifacts that were created.
        """
        artifacts: List[MCPArtifact] = []

        for action in plan.actions:
            arch_content = (
                f"## Architecture Decision: {action.title}\n\n"
                f"Instruction: {action.instruction}\n"
                f"Status: {action.status}\n"
                f"Component: {action.title}\n"
                f"Dependencies: [derived from plan graph]\n"
            )

            artifact = MCPArtifact(
                artifact_id=f"arch-{uuid.uuid4().hex[:8]}",
                type="architecture_doc",
                content=arch_content,
                metadata={
                    "agent": self.AGENT_NAME,
                    "plan_id": plan.plan_id,
                    "action_id": action.action_id,
                },
            )
            self.db.save_artifact(artifact)

            # Register in WorldModel via PINN
            self.pinn.ingest_artifact(
                artifact_id=artifact.artifact_id,
                content=arch_content,
                parent_id=plan.plan_id,
            )

            artifacts.append(artifact)

        return artifacts
