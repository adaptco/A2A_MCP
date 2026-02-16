"""Core pipeline coordinator for multi-agent orchestration."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Dict, List

from agents.architecture_agent import ArchitectureAgent
from agents.coder import CoderAgent
from agents.managing_agent import ManagingAgent
from agents.orchestration_agent import OrchestrationAgent
from agents.pinn_agent import PINNAgent
from agents.tester import TesterAgent
from orchestrator.judge_orchestrator import get_judge_orchestrator
from orchestrator.storage import DBManager
from schemas.agent_artifacts import MCPArtifact
from schemas.project_plan import ProjectPlan


@dataclass
class PipelineResult:
    """Typed output of a full 5-agent pipeline run."""

    plan: ProjectPlan
    blueprint: ProjectPlan
    architecture_artifacts: List[MCPArtifact] = field(default_factory=list)
    code_artifacts: List[MCPArtifact] = field(default_factory=list)
    test_verdicts: List[Dict[str, str]] = field(default_factory=list)
    success: bool = False


class IntentEngine:
    """Coordinates multi-agent execution across the full swarm."""

    def __init__(self) -> None:
        self.manager = ManagingAgent()
        self.orchestrator = OrchestrationAgent()
        self.architect = ArchitectureAgent()
        self.coder = CoderAgent()
        self.tester = TesterAgent()
        self.pinn = PINNAgent()
        self.judge = get_judge_orchestrator()
        self.db = DBManager()

    async def run_full_pipeline(
        self,
        description: str,
        requester: str = "system",
        max_healing_retries: int = 3,
    ) -> PipelineResult:
        """Run the full Managing -> Orchestrator -> Architect -> Coder -> Tester flow."""
        result = PipelineResult(
            plan=ProjectPlan(
                plan_id="pending",
                project_name=description[:80],
                requester=requester,
            ),
            blueprint=ProjectPlan(
                plan_id="pending",
                project_name=description[:80],
                requester=requester,
            ),
        )

        plan = await self.manager.categorize_project(description, requester)
        result.plan = plan

        task_descriptions = [a.instruction for a in plan.actions]
        blueprint = await self.orchestrator.build_blueprint(
            project_name=plan.project_name,
            task_descriptions=task_descriptions,
            requester=requester,
        )
        result.blueprint = blueprint

        arch_artifacts = await self.architect.map_system(blueprint)
        result.architecture_artifacts = arch_artifacts

        for action in blueprint.actions:
            action.status = "in_progress"

            coder_context = self.judge.get_agent_system_context("CoderAgent")
            coding_task = (
                f"{coder_context}\n\n"
                "Implement this task with tests and safety checks:\n"
                f"{action.instruction}"
            )
            artifact = await self.coder.generate_solution(
                parent_id=blueprint.plan_id,
                feedback=coding_task,
            )
            self.db.save_artifact(artifact)

            healed = False
            for attempt in range(max_healing_retries):
                report = await self.tester.validate(artifact.artifact_id)
                judgment = self.judge.judge_action(
                    action=(
                        f"TesterAgent verdict for {artifact.artifact_id}: "
                        f"{report.status}"
                    ),
                    context={
                        "attempt": attempt + 1,
                        "max_retries": max_healing_retries,
                        "artifact_id": artifact.artifact_id,
                    },
                    agent_name="TesterAgent",
                )
                result.test_verdicts.append(
                    {
                        "artifact": artifact.artifact_id,
                        "status": report.status,
                        "judge_score": f"{judgment.overall_score:.3f}",
                    }
                )

                if report.status == "PASS":
                    healed = True
                    break

                refine_context = self.judge.get_agent_system_context("CoderAgent")
                artifact = await self.coder.generate_solution(
                    parent_id=artifact.artifact_id,
                    feedback=(
                        f"{refine_context}\n\n"
                        f"Tester feedback:\n{report.critique}"
                    ),
                )
                self.db.save_artifact(artifact)

            result.code_artifacts.append(artifact)
            action.status = "completed" if healed else "failed"

        result.success = all(a.status == "completed" for a in blueprint.actions)
        return result

    async def execute_plan(self, plan: ProjectPlan) -> List[str]:
        """Legacy action-level coder->tester loop for backward compatibility."""
        artifact_ids: List[str] = []

        for action in plan.actions:
            action.status = "in_progress"
            parent_id = artifact_ids[-1] if artifact_ids else "project-plan-root"

            # 1. Generate Solution
            code_artifact = await self.coder.generate_solution(
                parent_id=parent_id,
                feedback=action.instruction,
            )
            artifact_ids.append(code_artifact.artifact_id)

            # 2. Validate with Tester
            report = await self.tester.validate(code_artifact.artifact_id)
            action.validation_feedback = report.critique

            # 3. Save Test Report
            test_artifact_id = str(uuid.uuid4())
            report_artifact = SimpleNamespace(
                artifact_id=test_artifact_id,
                parent_artifact_id=code_artifact.artifact_id,
                agent_name=self.tester.agent_name,
                version="1.0.0",
                type="test_report",
                content=report.model_dump_json(),
            )
            self.db.save_artifact(report_artifact)
            artifact_ids.append(test_artifact_id)

            # 4. Ingest into PINN (Vector Store)
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
                content=token.model_dump_json(),
            )
            self.db.save_artifact(pinn_artifact)
            artifact_ids.append(pinn_artifact_id)

            action.status = "completed" if report.status == "PASS" else "failed"

        return artifact_ids
