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
    """Coordinates coder, tester, and PINN agents for a project plan."""

    def __init__(self) -> None:
        self.coder = CoderAgent()
        self.tester = TesterAgent()
        self.pinn = PINNAgent()
        self.db = DBManager()

    async def execute_plan(self, plan: ProjectPlan) -> List[str]:
        artifact_ids: List[str] = []

        # Important: this must always point to the latest *code* artifact, not
        # the latest entry in artifact_ids (which also includes test/vector IDs).
        parent_code_artifact_id = plan.plan_id

        for action in plan.actions:
            action.status = "in_progress"

            try:
                code_artifact = await self.coder.generate_solution(
                    parent_id=parent_code_artifact_id,
                    feedback=action.validation_feedback or action.instruction,
                )
                artifact_ids.append(code_artifact.artifact_id)

                test_report = await self.tester.validate(code_artifact.artifact_id)
                test_artifact = MCPArtifact(
                    artifact_id=str(uuid.uuid4()),
                    type="test_report",
                    content=test_report.model_dump_json(),
                )
                self.db.save_artifact(test_artifact)
                artifact_ids.append(test_artifact.artifact_id)

                vector_token = self.pinn.ingest_artifact(
                    artifact_id=code_artifact.artifact_id,
                    content=code_artifact.content,
                    parent_id=parent_code_artifact_id,
                )
                artifact_ids.append(vector_token.token_id)

                action.validation_feedback = test_report.critique
                action.status = "completed" if test_report.status.upper() == "PASS" else "failed"

                # Chain next action from latest generated code artifact.
                parent_code_artifact_id = code_artifact.artifact_id

            except Exception as exc:  # defensive orchestration guard
                action.status = "failed"
                action.validation_feedback = str(exc)

        return artifact_ids
