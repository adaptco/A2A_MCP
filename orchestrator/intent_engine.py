"""Core pipeline coordinator for multi-agent orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from agents.architecture_agent import ArchitectureAgent
from agents.coder import CoderAgent
from agents.managing_agent import ManagingAgent
from agents.orchestration_agent import OrchestrationAgent
from agents.tester import TesterAgent
from orchestrator.judge_orchestrator import get_judge_orchestrator
from orchestrator.notifier import (
    WhatsAppNotifier,
    send_pipeline_completion_notification,
)
from orchestrator.storage import DBManager
from orchestrator.vector_gate import VectorGate, VectorGateDecision
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
        self.judge = get_judge_orchestrator()
        self.whatsapp_notifier = WhatsAppNotifier.from_env()
        self.vector_gate = VectorGate()
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
            coder_gate = self.vector_gate.evaluate(
                node="coder_input",
                query=f"{action.title}\n{action.instruction}",
                world_model=self.architect.pinn.world_model,
            )
            coder_vector_context = self.vector_gate.format_prompt_context(coder_gate)
            coding_task = (
                f"{coder_context}\n\n"
                f"{coder_vector_context}\n\n"
                "Implement this task with tests and safety checks:\n"
                f"{action.instruction}"
            )
            artifact = await self._generate_with_gate(
                parent_id=blueprint.plan_id,
                feedback=coding_task,
                context_tokens=coder_gate.matches,
            )
            self._attach_gate_metadata(artifact, coder_gate)
            self.db.save_artifact(artifact)

            healed = False
            for attempt in range(max_healing_retries):
                tester_gate = self.vector_gate.evaluate(
                    node="tester_input",
                    query=f"{action.instruction}\n{getattr(artifact, 'content', '')}",
                    world_model=self.architect.pinn.world_model,
                )
                tester_context = self.vector_gate.format_prompt_context(tester_gate)
                report = await self._validate_with_gate(
                    artifact_id=artifact.artifact_id,
                    supplemental_context=tester_context,
                    context_tokens=tester_gate.matches,
                )
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
                        "vector_gate": "open" if tester_gate.is_open else "closed",
                        "judge_score": f"{judgment.overall_score:.3f}",
                    }
                )

                if report.status == "PASS":
                    healed = True
                    break

                refine_context = self.judge.get_agent_system_context("CoderAgent")
                healing_gate = self.vector_gate.evaluate(
                    node="healing_input",
                    query=f"{action.instruction}\n{report.critique}",
                    world_model=self.architect.pinn.world_model,
                )
                healing_vector_context = self.vector_gate.format_prompt_context(healing_gate)
                artifact = await self._generate_with_gate(
                    parent_id=artifact.artifact_id,
                    feedback=(
                        f"{refine_context}\n\n"
                        f"{healing_vector_context}\n\n"
                        f"Tester feedback:\n{report.critique}"
                    ),
                    context_tokens=healing_gate.matches,
                )
                self._attach_gate_metadata(artifact, healing_gate)
                self.db.save_artifact(artifact)

            result.code_artifacts.append(artifact)
            action.status = "completed" if healed else "failed"

        result.success = all(a.status == "completed" for a in blueprint.actions)
        completed_actions = sum(1 for action in blueprint.actions if action.status == "completed")
        failed_actions = sum(1 for action in blueprint.actions if action.status == "failed")
        self._notify_completion(
            project_name=blueprint.project_name,
            success=result.success,
            completed_actions=completed_actions,
            failed_actions=failed_actions,
        )
        return result

    async def execute_plan(self, plan: ProjectPlan) -> List[str]:
        """Legacy action-level coder->tester loop for backward compatibility."""
        artifact_ids: List[str] = []

        for action in plan.actions:
            action.status = "in_progress"

            coder_gate = self.vector_gate.evaluate(
                node="legacy_coder_input",
                query=f"{action.title}\n{action.instruction}",
                world_model=self.architect.pinn.world_model,
            )
            coder_vector_context = self.vector_gate.format_prompt_context(coder_gate)
            artifact = await self._generate_with_gate(
                parent_id=plan.plan_id,
                feedback=f"{coder_vector_context}\n\n{action.instruction}",
                context_tokens=coder_gate.matches,
            )
            self._attach_gate_metadata(artifact, coder_gate)
            artifact_ids.append(artifact.artifact_id)

            tester_gate = self.vector_gate.evaluate(
                node="legacy_tester_input",
                query=f"{action.instruction}\n{getattr(artifact, 'content', '')}",
                world_model=self.architect.pinn.world_model,
            )
            tester_context = self.vector_gate.format_prompt_context(tester_gate)
            report = await self._validate_with_gate(
                artifact_id=artifact.artifact_id,
                supplemental_context=tester_context,
                context_tokens=tester_gate.matches,
            )
            artifact_ids.append(report.status)

            healing_gate = self.vector_gate.evaluate(
                node="legacy_healing_input",
                query=f"{action.instruction}\n{report.critique}",
                world_model=self.architect.pinn.world_model,
            )
            healing_vector_context = self.vector_gate.format_prompt_context(healing_gate)
            refined = await self._generate_with_gate(
                parent_id=artifact.artifact_id,
                feedback=f"{healing_vector_context}\n\n{report.critique}",
                context_tokens=healing_gate.matches,
            )
            self._attach_gate_metadata(refined, healing_gate)
            # Compatibility path for tests/mocks that return unsaved ad-hoc artifacts.
            if not hasattr(refined, "agent_name"):
                self.db.save_artifact(refined)
            artifact_ids.append(refined.artifact_id)

            action.status = "completed"

        self._notify_completion(
            project_name=plan.project_name,
            success=True,
            completed_actions=len(plan.actions),
            failed_actions=0,
        )
        return artifact_ids

    def _notify_completion(
        self,
        *,
        project_name: str,
        success: bool,
        completed_actions: int,
        failed_actions: int,
    ) -> None:
        """Send best-effort completion notification without breaking execution."""
        try:
            send_pipeline_completion_notification(
                self.whatsapp_notifier,
                project_name=project_name,
                success=success,
                completed_actions=completed_actions,
                failed_actions=failed_actions,
            )
        except Exception:
            # Notifications are out-of-band and must never break task execution.
            pass

    async def _validate_with_gate(
        self,
        artifact_id: str,
        supplemental_context: str,
        context_tokens,
    ):
        """
        Validate artifacts with vector context when supported.

        Some tests patch TesterAgent.validate with a one-arg coroutine; in that
        case we gracefully fall back to the legacy call signature.
        """
        try:
            return await self.tester.validate(
                artifact_id,
                supplemental_context=supplemental_context,
                context_tokens=context_tokens,
            )
        except TypeError:
            try:
                return await self.tester.validate(
                    artifact_id,
                    supplemental_context=supplemental_context,
                )
            except TypeError:
                return await self.tester.validate(artifact_id)

    async def _generate_with_gate(self, parent_id: str, feedback: str, context_tokens):
        """
        Generate artifacts with token context when supported.

        Some tests patch CoderAgent.generate_solution with a legacy two-arg
        signature, so this preserves backward compatibility.
        """
        try:
            return await self.coder.generate_solution(
                parent_id=parent_id,
                feedback=feedback,
                context_tokens=context_tokens,
            )
        except TypeError:
            return await self.coder.generate_solution(
                parent_id=parent_id,
                feedback=feedback,
            )

    @staticmethod
    def _attach_gate_metadata(artifact: object, decision: VectorGateDecision) -> None:
        """Attach gate provenance to artifacts that expose a metadata attribute."""
        if not hasattr(artifact, "metadata"):
            return

        metadata = getattr(artifact, "metadata") or {}
        metadata["vector_gate"] = {
            "node": decision.node,
            "is_open": decision.is_open,
            "threshold": decision.threshold,
            "top_score": decision.top_score,
            "match_count": len(decision.matches),
            "matched_token_ids": [m.token_id for m in decision.matches],
        }
        setattr(artifact, "metadata", metadata)
