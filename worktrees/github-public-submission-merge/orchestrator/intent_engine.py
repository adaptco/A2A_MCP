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

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

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


@dataclass
class ReleaseWebhookRequest:
    """Normalized release webhook payload across providers."""

    provider: str
    event_type: str
    repository: str
    release_tag: str
    release_name: str
    commit_sha: str
    triggered_by: str


class IntentEngine:
    """Coordinates multi-agent execution across the full swarm."""

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)
        self.manager = ManagingAgent()
        self.orchestrator = OrchestrationAgent()
        self.architect = ArchitectureAgent()
        self.coder = CoderAgent()
        self.tester = TesterAgent()
        self.db = DBManager()

    def normalize_release_webhook(
        self,
        payload: Dict[str, Any],
        provider: str = "generic",
        event_type: str = "release",
    ) -> ReleaseWebhookRequest:
        """Map provider-specific payload fields into a stable release request."""
        repository = (
            payload.get("repository", {}).get("full_name")
            if isinstance(payload.get("repository"), dict)
            else payload.get("repository")
        ) or "unknown-repository"

        release_tag = (
            payload.get("release", {}).get("tag_name")
            if isinstance(payload.get("release"), dict)
            else None
        ) or payload.get("tag")
        if not release_tag and isinstance(payload.get("ref"), str):
            release_tag = payload["ref"].replace("refs/tags/", "")
        release_tag = release_tag or "untagged"

        release_name = (
            payload.get("release", {}).get("name")
            if isinstance(payload.get("release"), dict)
            else None
        ) or payload.get("name") or release_tag

        commit_sha = payload.get("after")
        if not commit_sha and isinstance(payload.get("head_commit"), dict):
            commit_sha = payload.get("head_commit", {}).get("id")
        if not commit_sha and isinstance(payload.get("release"), dict):
            commit_sha = payload.get("release", {}).get("target_commitish")
        commit_sha = commit_sha or ""

        triggered_by = (
            payload.get("sender", {}).get("login")
            if isinstance(payload.get("sender"), dict)
            else None
        ) or (
            payload.get("pusher", {}).get("name")
            if isinstance(payload.get("pusher"), dict)
            else None
        ) or "webhook"

        return ReleaseWebhookRequest(
            provider=provider,
            event_type=event_type,
            repository=repository,
            release_tag=release_tag,
            release_name=release_name,
            commit_sha=commit_sha,
            triggered_by=triggered_by,
        )

    def _persist_release_summary(
        self,
        summary: Dict[str, Any],
        webhook_payload: Dict[str, Any],
    ) -> None:
        """Best-effort persistence of release execution metadata."""
        payload_preview = {
            "repository": summary.get("repository"),
            "release_tag": summary.get("release_tag"),
            "event_type": summary.get("event_type"),
            "provider": summary.get("provider"),
        }
        artifact = MCPArtifact(
            artifact_id=f"release-report-{uuid.uuid4()}",
            type="release_report",
            content=json.dumps(summary, sort_keys=True),
            metadata={
                "payload_preview": payload_preview,
                "webhook_keys": sorted(webhook_payload.keys()),
            },
        )
        try:
            self.db.save_artifact(artifact)
        except Exception as exc:  # pragma: no cover - should not fail release path
            self.logger.warning("Failed to persist release summary artifact: %s", exc)

    async def run_release_workflow_from_webhook(
        self,
        payload: Dict[str, Any],
        provider: str = "generic",
        event_type: str = "release",
        max_healing_retries: int = 3,
    ) -> Dict[str, Any]:
        """
        Execute the full release pipeline from a webhook payload.

        Returns a compact, serializable summary suitable for webhook job status APIs.
        """
        req = self.normalize_release_webhook(
            payload=payload,
            provider=provider,
            event_type=event_type,
        )
        description = (
            f"Release {req.release_tag} ({req.release_name}) for {req.repository}. "
            f"Event={req.event_type}. Commit={req.commit_sha or 'unknown'}."
        )
        pipeline_result = await self.run_full_pipeline(
            description=description,
            requester=f"webhook:{req.triggered_by}",
            max_healing_retries=max_healing_retries,
        )
        completed_actions = sum(
            1 for action in pipeline_result.blueprint.actions if action.status == "completed"
        )
        summary = {
            "provider": req.provider,
            "event_type": req.event_type,
            "repository": req.repository,
            "release_tag": req.release_tag,
            "release_name": req.release_name,
            "commit_sha": req.commit_sha,
            "triggered_by": req.triggered_by,
            "success": pipeline_result.success,
            "plan_id": pipeline_result.plan.plan_id,
            "blueprint_id": pipeline_result.blueprint.plan_id,
            "actions_total": len(pipeline_result.blueprint.actions),
            "actions_completed": completed_actions,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._persist_release_summary(summary=summary, webhook_payload=payload)
        return summary

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
            self.db.save_artifact(artifact)

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
                self.db.save_artifact(artifact)

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
            self.db.save_artifact(artifact)
            artifact_ids.append(artifact.artifact_id)

            # Validate the artifact
            report = await self.tester.validate(artifact.artifact_id)
            artifact_ids.append(report.status)

            # Produce a refinement pass
            refined = await self.coder.generate_solution(
                parent_id=artifact.artifact_id,
                feedback=report.critique,
            )
            self.db.save_artifact(refined)
            artifact_ids.append(refined.artifact_id)

            action.status = "completed"

        return artifact_ids
