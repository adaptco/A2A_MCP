from __future__ import annotations

import uuid
from typing import List

from agents.coder import CoderAgent
from agents.pinn_agent import PINNAgent
from agents.tester import TesterAgent
from orchestrator.storage import DBManager
from schemas.agent_artifacts import MCPArtifact
from schemas.project_plan import ProjectPlan


class IntentEngine:
    """Coordinates coder/tester/PINN execution for a project plan."""

    def __init__(self) -> None:
        self.db = DBManager()
        self.coder = CoderAgent()
        self.tester = TesterAgent()
        self.pinn = PINNAgent()

    async def execute_plan(self, plan: ProjectPlan) -> List[str]:
        artifact_ids: List[str] = []
        parent_id = plan.plan_id

        for action in plan.actions:
            action.status = "in_progress"

            artifact = await self.coder.generate_solution(
                parent_id=parent_id,
                feedback=action.instruction,
            )
            self.db.save_artifact(artifact)
            artifact_ids.append(artifact.artifact_id)

            report = await self.tester.validate(artifact.artifact_id)
            report_artifact = MCPArtifact(
                artifact_id=str(uuid.uuid4()),
                parent_artifact_id=artifact.artifact_id,
                agent_name=getattr(self.tester, "agent_name", "TesterAgent-Alpha"),
                version="1.0.0",
                type="test_report",
                content=report.model_dump_json(),
            )
            self.db.save_artifact(report_artifact)
            artifact_ids.append(report_artifact.artifact_id)

            pinn_token = self.pinn.ingest_artifact(
                artifact_id=artifact.artifact_id,
                content=str(artifact.content),
                parent_id=parent_id,
            )
            artifact_ids.append(pinn_token.token_id)

            if report.status == "PASS":
                action.status = "completed"
                action.validation_feedback = report.critique
                parent_id = artifact.artifact_id
                continue

            action.status = "failed"
            action.validation_feedback = report.critique

            retry_artifact = await self.coder.generate_solution(
                parent_id=artifact.artifact_id,
                feedback=report.critique,
            )
            self.db.save_artifact(retry_artifact)
            artifact_ids.append(retry_artifact.artifact_id)

            retry_report = await self.tester.validate(retry_artifact.artifact_id)
            retry_report_artifact = MCPArtifact(
                artifact_id=str(uuid.uuid4()),
                parent_artifact_id=retry_artifact.artifact_id,
                agent_name=getattr(self.tester, "agent_name", "TesterAgent-Alpha"),
                version="1.0.0",
                type="test_report",
                content=retry_report.model_dump_json(),
            )
            self.db.save_artifact(retry_report_artifact)
            artifact_ids.append(retry_report_artifact.artifact_id)

            self.pinn.ingest_artifact(
                artifact_id=retry_artifact.artifact_id,
                content=str(retry_artifact.content),
                parent_id=artifact.artifact_id,
            )

            if retry_report.status != "PASS":
                raise RuntimeError(
                    f"Plan action {action.action_id} failed after retry: {retry_report.critique}"
                )

            action.status = "completed"
            action.validation_feedback = retry_report.critique
            parent_id = retry_artifact.artifact_id

        return artifact_ids

    async def process_plan(self, plan: ProjectPlan) -> List[str]:
        """Backward-compatible wrapper for legacy callers."""
        return await self.execute_plan(plan)
