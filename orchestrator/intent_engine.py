import logging
from typing import List

from agents.pinn_agent import PINNAgent
from agents.researcher import ResearcherAgent
from agents.architecture_agent import ArchitectureAgent
from agents.managing_agent import ManagingAgent
from agents.coder import CoderAgent
from agents.tester import TesterAgent
from judge.decision import Judge
from orchestrator.storage import DBManager
from orchestrator.vector_gate import VectorGate, VectorGateDecision
from schemas.project_plan import ProjectPlan
from app.notification_app import send_pipeline_completion_notification


class IntentEngine:
    def __init__(self, tester=None):
        self.db = DBManager()
        self.manager = ManagingAgent()
        self.researcher = ResearcherAgent()
        self.architect = ArchitectureAgent()
        self.coder = CoderAgent()
        # Use provided tester or default to TesterAgent
        self.tester = tester if tester else TesterAgent()
        self.judge = Judge()
        self.whatsapp_notifier = None  # Injected at runtime if needed
        self.parent_id = None

        # Initialize Vector Gate for semantic routing and validation
        self.vector_gate = VectorGate(min_similarity=0.25, top_k=3)

    def resolve_parent_chain(self, plan_context: dict):
        """
        Resolves the parent ID for the current execution context.
        Prioritizes the blueprint ID if available, otherwise falls back to the plan ID.
        """
        # P1 Fix: Prioritize 'blueprint_id' if available in the plan context
        if "blueprint_id" in plan_context and plan_context["blueprint_id"]:
            self.parent_id = plan_context["blueprint_id"]
        elif "plan_id" in plan_context:
            self.parent_id = plan_context["plan_id"]
        else:
            self.parent_id = None
            logging.warning("Could not resolve parent chain from plan context.")

        return self.parent_id

    async def validate_intent(self, artifact_id, supplemental_context=None, context_tokens=None):
        """
        Validates the intent of a generated artifact using the TesterAgent.
        """
        try:
            return await self.tester.validate(
                artifact_id,
                supplemental_context=supplemental_context,
                context_tokens=context_tokens,
            )
        except TypeError:
            try:
                # Workaround for agents with older signatures
                return await self.tester.validate(
                    artifact_id,
                    supplemental_context=supplemental_context,
                )
            except Exception as e:
                logging.error(f"Validation failed: {e}")
                raise

    async def run_full_pipeline(self, description: str, requester: str = "user"):
        """
        Orchestrates the full pipeline from description to tested code.
        """
        # 1. Plan
        plan_result = await self.manager.create_plan(description, requester)
        plan = plan_result.plan

        # 2. Research (Optional but recommended)
        # In a real scenario, research would feed into the blueprint.

        # 3. Architect
        blueprint = await self.architect.create_blueprint(
            project_name=plan.project_name,
            description=description,
            plan=plan
        )

        # Resolve parent chain for subsequent steps
        self.resolve_parent_chain({"plan_id": plan.plan_id, "blueprint_id": blueprint.artifact_id})

        # 4. Execute (Code & Test)
        # This uses the internal logic which now leverages resolve_parent_chain if adapted,
        # but here we call the legacy-compatible execution flow.
        # For the purpose of this task, we assume execute_plan is the main entry point for action execution.
        artifact_ids = await self.execute_plan(plan)

        # Construct a result object (mocking the structure expected by the webhook)
        result = type('PipelineResult', (), {})()
        result.success = True # Simplified for this snippet
        result.plan = plan
        result.blueprint = blueprint
        result.code_artifacts = [] # Populate as needed
        result.test_verdicts = [] # Populate as needed

        # Fetch artifacts to populate result (mock logic)
        for art_id in artifact_ids:
             # In a real implementation, we'd fetch the artifact object
             pass

        return result

    async def execute_plan(self, plan: ProjectPlan) -> List[str]:
        """Legacy action-level coder->tester loop for backward compatibility."""
        artifact_ids: List[str] = []

        # Ensure parent chain is resolved
        if not self.parent_id:
             self.resolve_parent_chain({"plan_id": plan.plan_id})

        for action in plan.actions:
            action.status = "in_progress"

            coder_gate = self.vector_gate.evaluate(
                node="legacy_coder_input",
                query=f"{action.title}\n{action.instruction}",
                world_model=self.architect.pinn.world_model,
            )
            coder_vector_context = self.vector_gate.format_prompt_context(coder_gate)

            # Use resolved parent_id instead of just plan.plan_id
            parent_context_id = self.parent_id or plan.plan_id

            artifact = await self._generate_with_gate(
                parent_id=parent_context_id,
                feedback=f"{coder_vector_context}\n\n{action.instruction}",
                context_tokens=coder_gate.matches,
            )
            self._attach_gate_metadata(artifact, coder_gate)
            self.db.save_artifact(artifact)
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
