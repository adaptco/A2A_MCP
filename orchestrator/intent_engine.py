# A2A_MCP/orchestrator/intent_engine.py
"""
IntentEngine — Core pipeline coordinator.

Provides two execution modes:

1. ``execute_plan(plan)`` — legacy action-level Coder→Tester loop.
2. ``run_full_pipeline(description)`` — full 5-agent end-to-end pipeline:
      ManagingAgent → OrchestrationAgent → ArchitectureAgent
                                          → CoderAgent → TesterAgent
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from agents.architecture_agent import ArchitectureAgent
from agents.coder import CoderAgent
from agents.managing_agent import ManagingAgent
from agents.orchestration_agent import OrchestrationAgent
from agents.tester import TesterAgent
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
        self.db = DBManager()

    # ------------------------------------------------------------------
    # Full 5-agent pipeline
    # ------------------------------------------------------------------

    async def run_full_pipeline(
        self,
        description: str,
        requester: str = "system",
        max_healing_retries: int = 3,
    ) -> PipelineResult:
        """
        End-to-end orchestration:

        1. **ManagingAgent** — categorise *description* into PlanActions.
        2. **OrchestrationAgent** — build a typed blueprint with delegation.
        3. **ArchitectureAgent** — map system architecture + WorldModel.
        4. **CoderAgent** — generate code artifacts for each action.
        5. **TesterAgent** — validate artifacts; self-heal on failure.

        Returns a ``PipelineResult`` with all intermediary artefacts.
        """
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

        # ── Stage 1: ManagingAgent ──────────────────────────────────
        plan = await self.manager.categorize_project(description, requester)
        result.plan = plan

        # ── Stage 2: OrchestrationAgent ─────────────────────────────
        task_descriptions = [a.instruction for a in plan.actions]
        blueprint = await self.orchestrator.build_blueprint(
            project_name=plan.project_name,
            task_descriptions=task_descriptions,
            requester=requester,
        )
        result.blueprint = blueprint

        # ── Stage 3: ArchitectureAgent ──────────────────────────────
        arch_artifacts = await self.architect.map_system(blueprint)
        result.architecture_artifacts = arch_artifacts

        # ── Stage 4 + 5: CoderAgent → TesterAgent (self-healing) ────
        for action in blueprint.actions:
            action.status = "in_progress"

            artifact = await self.coder.generate_solution(
                parent_id=blueprint.plan_id,
                feedback=action.instruction,
            )


            # Self-healing loop
            healed = False
            for attempt in range(max_healing_retries):
                report = await self.tester.validate(artifact.artifact_id)
                result.test_verdicts.append(
                    {"artifact": artifact.artifact_id, "status": report.status}
                )

                if report.status == "PASS":
                    healed = True
                    break

                # Re-generate with tester feedback
                artifact = await self.coder.generate_solution(
                    parent_id=artifact.artifact_id,
                    feedback=report.critique,
                )


            result.code_artifacts.append(artifact)
            action.status = "completed" if healed else "failed"

        result.success = all(
            a.status == "completed" for a in blueprint.actions
        )
        return result

    # ------------------------------------------------------------------
    # Legacy action-level loop (backward compat)
    # ------------------------------------------------------------------

    async def execute_plan(self, plan: ProjectPlan) -> List[str]:
        """
        Walk through every action in the plan, invoking the coder and tester
        for each one, and return a list of all artifact IDs produced.
        """
        artifact_ids: List[str] = []

        for action in plan.actions:
            action.status = "in_progress"

            # Generate code solution
            artifact = await self.coder.generate_solution(
                parent_id=plan.plan_id,
                feedback=action.instruction,
            )

            artifact_ids.append(artifact.artifact_id)

            # Validate the artifact
            report = await self.tester.validate(artifact.artifact_id)
            artifact_ids.append(report.status)

            # Produce a refinement pass
            refined = await self.coder.generate_solution(
                parent_id=artifact.artifact_id,
                feedback=report.critique,
            )

            artifact_ids.append(refined.artifact_id)

            action.status = "completed"

        return artifact_ids
