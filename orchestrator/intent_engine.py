from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import List

from agents.coder import CoderAgent
from agents.pinn_agent import PINNAgent
from agents.tester import TesterAgent
from orchestrator.storage import DBManager
from schemas.project_plan import ProjectPlan


class IntentEngine:
    """Orchestrates project-plan execution across coder/tester/PINN agents."""

    def __init__(self) -> None:
        self.db = DBManager()
        self.coder = CoderAgent()
        self.tester = TesterAgent()
        self.pinn = PINNAgent()

    async def execute_plan(self, plan: ProjectPlan) -> List[str]:
        artifact_ids: List[str] = []

        for action in plan.actions:
            action.status = "in_progress"
            parent_id = artifact_ids[-1] if artifact_ids else "project-plan-root"

            code_artifact = await self.coder.generate_solution(
                parent_id=parent_id,
                feedback=action.instruction,
            )
            artifact_ids.append(code_artifact.artifact_id)

            report = await self.tester.validate(code_artifact.artifact_id)
            action.validation_feedback = report.critique

            test_artifact_id = str(uuid.uuid4())
            report_artifact = SimpleNamespace(
                artifact_id=test_artifact_id,
                parent_artifact_id=code_artifact.artifact_id,
                agent_name=self.tester.agent_name,
                version="1.0.0",
                type="test_report",
                content=report.json(),
            )
            self.db.save_artifact(report_artifact)
            artifact_ids.append(test_artifact_id)

            pinn_artifact_id = str(uuid.uuid4())
            token = self.pinn.ingest_artifact(
                artifact_id=pinn_artifact_id,
                content=code_artifact.content,
                parent_id=code_artifact.artifact_id,
            )
            pinn_artifact = SimpleNamespace(
                artifact_id=pinn_artifact_id,
                parent_artifact_id=code_artifact.artifact_id,
                agent_name=self.pinn.agent_name,
                version="1.0.0",
                type="vector_token",
                content=token.json(),
            )
            self.db.save_artifact(pinn_artifact)
            artifact_ids.append(pinn_artifact_id)

            action.status = "completed" if report.status == "PASS" else "failed"

        return artifact_ids
