"""Core pipeline coordinator for multi-agent orchestration."""

from __future__ import annotations

import logging
import os
import uuid
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Dict, List, Any

from agents.architecture_agent import ArchitectureAgent
from agents.coder import CoderAgent
from agents.managing_agent import ManagingAgent
from agents.orchestration_agent import OrchestrationAgent
from agents.pinn_agent import PINNAgent
from agents.tester import TesterAgent
from orchestrator.judge_orchestrator import get_judge_orchestrator
from orchestrator.stateflow import StateMachine, State
from orchestrator.storage import DBManager
from orchestrator.vector_gate import VectorGate, VectorGateDecision
from schemas.agent_artifacts import MCPArtifact
from schemas.project_plan import ProjectPlan, PlanAction


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
    """Coordinates multi-agent execution across the full swarm with physics-informed verification."""

    _logger = logging.getLogger("IntentEngine")

    def __init__(self, sm: StateMachine | None = None) -> None:
        self.manager = ManagingAgent()
        self.orchestrator = OrchestrationAgent()
        self.architect = ArchitectureAgent()
        self.coder = CoderAgent()
        self.tester = TesterAgent()
        self.pinn = PINNAgent()
        self.judge = get_judge_orchestrator()
        self.db = DBManager()
        self.vector_gate = VectorGate()
        self.sm = sm

        # RBAC integration (optional, gracefully degrades)
        self._rbac_enabled = os.getenv("RBAC_ENABLED", "true").lower() == "true"
        self._rbac_client = None
        if self._rbac_enabled:
            try:
                from rbac.client import RBACClient
                rbac_url = os.getenv("RBAC_URL", "http://rbac-gateway:8001")
                self._rbac_client = RBACClient(rbac_url)
            except ImportError:
                self._logger.warning("rbac package not installed — RBAC disabled.")

    async def run_full_pipeline(
        self,
        description: str,
        requester: str = "system",
        max_healing_retries: int = 3,
    ) -> PipelineResult:
        """
        End-to-end orchestration with Prime Directive lifecycle:

        1. **ManagingAgent** — categorise objective.
        2. **OrchestrationAgent** — build blueprint.
        3. **ArchitectureAgent** — map system + WorldModel.
        4. **CoderAgent** — generate code.
        5. **TesterAgent** — validate + self-heal.
        6. **Prime Directive** — formal PINN verification & export.
        """
        # RBAC gate
        if self._rbac_client and self._rbac_enabled:
            if not self._rbac_client.verify_permission(requester, action="run_pipeline"):
                raise PermissionError(f"Agent '{requester}' is not permitted to run the pipeline.")
            self._logger.info("RBAC: '%s' authorized for run_pipeline.", requester)

        result = PipelineResult(
            plan=ProjectPlan(plan_id="pending", project_name=description[:80], requester=requester),
            blueprint=ProjectPlan(plan_id="pending", project_name=description[:80], requester=requester),
        )

        plan = await self.manager.categorize_project(description, requester)
        result.plan = plan

        if self.sm:
            self.sm.trigger("RUN_DISPATCHED")

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
            coding_task = f"{coder_context}\n\nImplement this task:\n{action.instruction}"
            
            artifact = await self.coder.generate_solution(
                parent_id=blueprint.plan_id,
                feedback=coding_task,
            )
            self.db.save_artifact(artifact)

            # Self-healing loop
            healed = False
            for attempt in range(max_healing_retries):
                report = await self.tester.validate(artifact.artifact_id)
                judgment = self.judge.judge_action(
                    action=f"Tester verdict for {artifact.artifact_id}: {report.status}",
                    context={"attempt": attempt + 1, "artifact_id": artifact.artifact_id},
                    agent_name="TesterAgent",
                )
                result.test_verdicts.append({
                    "artifact": artifact.artifact_id,
                    "status": report.status,
                    "judge_score": f"{judgment.overall_score:.3f}",
                })

                if report.status == "PASS":
                    healed = True
                    break

                artifact = await self.coder.generate_solution(
                    parent_id=artifact.artifact_id,
                    feedback=f"Tester feedback:\n{report.critique}",
                )
                self.db.save_artifact(artifact)

            result.code_artifacts.append(artifact)
            action.status = "completed" if healed else "failed"

            if action.status == "completed":
                if self.sm and self.sm.state == State.EXECUTING:
                    self.sm.trigger("EXECUTION_COMPLETE")
                
                # Apply Prime Directive Cycle
                prime_success = await self._apply_prime_directive(artifact, action.title)
                if not prime_success:
                    action.status = "failed"
                    action.validation_feedback = "Prime Directive validation failed (residual too high)"
            
            if self.sm and self.sm.state == State.TERMINATED_SUCCESS:
                if action != blueprint.actions[-1]:
                    self.sm.override(State.EXECUTING, reason="Next action in blueprint")

        result.success = all(a.status == "completed" for a in blueprint.actions)
        return result

    async def _apply_prime_directive(self, artifact: MCPArtifact, action_title: str) -> bool:
        """Execute the Prime Directive lifecycle for a verified artifact."""
        if not self.sm:
            residual = self.pinn.calculate_residual(artifact.content)
            self._attach_pinn_metadata(artifact, residual)
            return True

        try:
            if self.sm.state == State.EVALUATING:
                self.sm.trigger("VERDICT_PASS")

            self.sm.trigger("PRIME_RENDER_COMPLETE")
            residual = self.pinn.calculate_residual(artifact.content)
            self._attach_pinn_metadata(artifact, residual)
            
            if residual > 0.15:
                self.sm.trigger("PRIME_VALIDATION_FAIL", residual=residual, reason="PINN residual above threshold")
                return False
            
            self.sm.trigger("PRIME_VALIDATION_PASS", residual=residual)
            self.sm.trigger("PRIME_EXPORT_COMPLETE")
            self.sm.trigger("PRIME_COMMIT_COMPLETE")
            return True
        except Exception as e:
            self._logger.error(f"Prime Directive cycle failed: {e}")
            return False

    @staticmethod
    def _attach_pinn_metadata(artifact: object, residual: float) -> None:
        """Attach PINN residual to artifact metadata."""
        if not hasattr(artifact, "metadata"):
            return
        metadata = getattr(artifact, "metadata") or {}
        metadata["pinn_validation"] = {
            "residual": residual,
            "status": "PASS" if residual <= 0.15 else "FAIL",
            "threshold": 0.15,
            "engine": "PINNAgent-Alpha"
        }
        setattr(artifact, "metadata", metadata)

    async def execute_plan(self, plan: ProjectPlan) -> List[str]:
        """Legacy action-level coder->tester loop for backward compatibility."""
        artifact_ids: List[str] = []
        last_code_artifact_id: str | None = None

        if self.sm and self.sm.state == State.IDLE:
            self.sm.trigger("OBJECTIVE_INGRESS")
            self.sm.trigger("RUN_DISPATCHED")

        for action in plan.actions:
            action.status = "in_progress"
            parent_id = last_code_artifact_id or plan.plan_id

            # Simplified legacy loop without full gate evaluation for brevity in merge
            artifact = await self.coder.generate_solution(parent_id=parent_id, feedback=action.instruction)
            if not self.db.get_artifact(artifact.artifact_id):
                self.db.save_artifact(artifact)
            
            artifact_ids.append(artifact.artifact_id)
            last_code_artifact_id = artifact.artifact_id

            report = await self.tester.validate(artifact.artifact_id)
            test_id = str(uuid.uuid4())
            self.db.save_artifact(SimpleNamespace(
                artifact_id=test_id, parent_artifact_id=artifact.artifact_id,
                agent_name=self.tester.agent_name, version="1.0.0", type="test_report",
                content=report.model_dump_json(), metadata={}
            ))
            artifact_ids.append(test_id)

            pinn_id = str(uuid.uuid4())
            token = await self.pinn.ingest_artifact(artifact_id=pinn_id, content=artifact.content, parent_id=artifact.artifact_id)
            self.db.save_artifact(SimpleNamespace(
                artifact_id=pinn_id, parent_artifact_id=artifact.artifact_id,
                agent_name=self.pinn.agent_name, version="1.0.0", type="vector_token",
                content=token.model_dump_json(), metadata={}
            ))
            artifact_ids.append(pinn_id)

            action.status = "completed" if report.status == "PASS" else "failed"
            if action.status == "completed" and self.sm:
                if self.sm.state == State.EXECUTING:
                    self.sm.trigger("EXECUTION_COMPLETE")
                await self._apply_prime_directive(artifact, action.title)
                if self.sm.state == State.TERMINATED_SUCCESS and action != plan.actions[-1]:
                    self.sm.override(State.EXECUTING, reason="Next action in plan")

        return artifact_ids
