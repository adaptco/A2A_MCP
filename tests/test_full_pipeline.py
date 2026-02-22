# tests/test_full_pipeline.py
"""
End-to-end test for the full 5-agent IntentEngine pipeline:
ManagingAgent → OrchestrationAgent → ArchitectureAgent → CoderAgent → TesterAgent.
"""
from __future__ import annotations

import asyncio
import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, AsyncMock

import pytest

from agents.tester import TestReport
from orchestrator.intent_engine import IntentEngine, PipelineResult


class TestFullPipeline:
    """Integration tests for IntentEngine.run_full_pipeline()."""

    def _make_engine(
        self,
        llm_categorisation: str = "1. Design schema\n2. Build API",
        llm_code: str = "def main(): pass",
        test_verdicts: list | None = None,
    ) -> IntentEngine:
        """
        Build an IntentEngine with every external dependency mocked:
        - ManagingAgent.llm → returns *llm_categorisation*
        - CoderAgent.llm → returns *llm_code*
        - TesterAgent.llm → produces *test_verdicts* (default: all PASS)
        - All DB calls → no-op
        """
        mock_architect = MagicMock()
        mock_coder = MagicMock()
        mock_tester = MagicMock()
        mock_db = MagicMock()
        mock_pinn = MagicMock()
        mock_manager = MagicMock()
        mock_orchestrator = MagicMock()

        # Setup mocks
        mock_pinn.world_model = MagicMock()

        engine = IntentEngine(
            architect=mock_architect,
            coder=mock_coder,
            tester=mock_tester,
            db=mock_db,
            pinn=mock_pinn,
            manager=mock_manager,
            orchestrator=mock_orchestrator
        )

        # ── Mock ManagingAgent ──────────────────────────────────────
        engine.manager.categorize_project = AsyncMock()
        # Ensure it returns a dummy plan so code doesn't crash before mocking return values in tests
        dummy_plan_mock = MagicMock()
        dummy_plan_mock.actions = []
        engine.manager.categorize_project.return_value = dummy_plan_mock

        # ── Mock OrchestrationAgent ─────────────────────────────────
        engine.orchestrator.build_blueprint = AsyncMock()
        # Return dummy blueprint
        engine.orchestrator.build_blueprint.return_value = dummy_plan_mock

        # ── Mock ArchitectureAgent ──────────────────────────────────
        engine.architect.map_system = AsyncMock(return_value=[])

        # ── Mock CoderAgent ─────────────────────────────────────────
        # Note: generate_solution is called by IntentEngine using await
        engine.coder.generate_solution = AsyncMock()
        engine.coder.generate_solution.return_value = SimpleNamespace(artifact_id="art-1", content="code")

        # ── Mock TesterAgent ────────────────────────────────────────
        if test_verdicts is None:
            test_verdicts = ["PASS"]

        # We need a mutable list that persists across calls
        verdicts_ref = list(test_verdicts)

        async def fake_validate(_artifact_id, supplemental_context=None, context_tokens=None):
            verdict = verdicts_ref.pop(0) if verdicts_ref else "PASS"
            return TestReport(
                status=verdict,
                critique="All clear" if verdict == "PASS" else "Bug found",
            )

        engine.tester.validate = fake_validate  # type: ignore[assignment]

        # ── Mock top-level DB ───────────────────────────────────────
        engine.db = MagicMock()

        # ── Mock Vector Gate ────────────────────────────────────────
        engine.vector_gate.evaluate = MagicMock()
        engine.vector_gate.evaluate.return_value.matches = []
        engine.vector_gate.format_prompt_context = MagicMock(return_value="")

        return engine

    # -----------------------------------------------------------------
    # Happy-path: every agent succeeds on the first try
    # -----------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_happy_path_all_pass(self):
        engine = self._make_engine()

        # Mock Plan (from Manager)
        plan_mock = MagicMock()
        plan_mock.actions = [MagicMock(instruction="do x")]
        engine.manager.categorize_project.return_value = plan_mock

        # Mock Blueprint (from Orchestrator)
        blueprint_mock = MagicMock()
        blueprint_mock.plan_id = "blueprint-123"
        blueprint_mock.actions = [MagicMock(instruction="do x", title="Task A", status="pending")]
        engine.orchestrator.build_blueprint.return_value = blueprint_mock

        # Mock Architecture
        engine.architect.map_system.return_value = [SimpleNamespace(type="architecture_doc")]

        # Mock Coder
        engine.coder.generate_solution.return_value = SimpleNamespace(artifact_id="art-1", content="code")

        result = await engine.run_pipeline("Build a user service", "proj1")

        assert isinstance(result, PipelineResult)
        assert result.success is True

        # Architect produced architecture artifacts
        assert len(result.architecture_artifacts) > 0

        # CoderAgent produced code artifacts
        assert len(result.code_artifacts) > 0

        # TesterAgent returned verdicts
        assert len(result.test_verdicts) > 0
        assert all(v["status"] == "PASS" for v in result.test_verdicts)

    # -----------------------------------------------------------------
    # Self-healing: first test fails, second pass succeeds
    # -----------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_self_healing_fail_then_pass(self):
        # For each blueprint action (2 tasks × 4 pipeline stages = 8 actions),
        # the first action will FAIL then PASS; remaining all PASS.
        verdicts = ["FAIL", "PASS"] + ["PASS"] * 20  # generous surplus
        engine = self._make_engine(test_verdicts=verdicts)

        # Mock Plan
        plan_mock = MagicMock()
        plan_mock.actions = [MagicMock(instruction="do x")]
        engine.manager.categorize_project.return_value = plan_mock

        # Mock Blueprint
        blueprint_mock = MagicMock()
        blueprint_mock.plan_id = "blueprint-123"
        # Only 1 action to test healing
        blueprint_mock.actions = [MagicMock(instruction="do x", title="Task A", status="pending")]
        engine.orchestrator.build_blueprint.return_value = blueprint_mock

        result = await engine.run_pipeline("Build something", "proj1")

        assert result.success is True
        # At least one FAIL verdict should appear in the trace
        statuses = [v["status"] for v in result.test_verdicts]
        assert "FAIL" in statuses
        assert "PASS" in statuses

    # -----------------------------------------------------------------
    # All actions fail all retries → pipeline reports failure
    # -----------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_all_fail_reports_failure(self):
        verdicts = ["FAIL"] * 100  # every attempt fails
        engine = self._make_engine(test_verdicts=verdicts)

        # Mock Plan
        plan_mock = MagicMock()
        plan_mock.actions = [MagicMock(instruction="do x")]
        engine.manager.categorize_project.return_value = plan_mock

        # Mock Blueprint
        blueprint_mock = MagicMock()
        blueprint_mock.project_name = "Doomed"
        blueprint_mock.plan_id = "blueprint-123"
        action = MagicMock(instruction="do x", title="Task A", status="pending")
        blueprint_mock.actions = [action]
        engine.orchestrator.build_blueprint.return_value = blueprint_mock

        result = await engine.run_pipeline(
            "Doomed project", "proj1", max_healing_retries=2
        )

        assert result.success is False
        # All blueprint actions should be marked "failed"
        assert action.status == "failed"

    # -----------------------------------------------------------------
    # Pipeline result contains correct artefact counts
    # -----------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_artifact_counts(self):
        engine = self._make_engine(
            llm_categorisation="1. Task A",  # 1 task → 4 pipeline stages
        )

        # Mock Plan
        plan_mock = MagicMock()
        plan_mock.actions = [MagicMock(instruction=f"do {i}") for i in range(4)]
        engine.manager.categorize_project.return_value = plan_mock

        # Mock Blueprint
        blueprint_mock = MagicMock()
        blueprint_mock.plan_id = "blueprint-123"
        # 4 actions
        blueprint_mock.actions = [
            MagicMock(instruction=f"do {i}", title=f"Task {i}", status="pending")
            for i in range(4)
        ]
        engine.orchestrator.build_blueprint.return_value = blueprint_mock

        # Mock Architecture
        engine.architect.map_system.return_value = [SimpleNamespace(type="architecture_doc") for _ in range(4)]

        result = await engine.run_pipeline("Single task project", "proj1")

        # architecture artifacts = one per blueprint action (mocked)
        assert len(result.architecture_artifacts) == 4

        # code artifacts = one final per blueprint action (happy path)
        assert len(result.code_artifacts) == 4

    # -----------------------------------------------------------------
    # Backward compatibility: execute_plan still works
    # -----------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_legacy_execute_plan_still_works(self):
        engine = self._make_engine()

        async def fake_generate(parent_id, feedback=None, context_tokens=None):
            return SimpleNamespace(
                artifact_id=str(uuid.uuid4()),
                content="code",
            )

        async def fake_validate(_aid, supplemental_context=None, context_tokens=None):
            return TestReport(status="PASS", critique="ok")

        engine.coder.generate_solution = fake_generate  # type: ignore
        engine.tester.validate = fake_validate  # type: ignore

        from schemas.project_plan import PlanAction, ProjectPlan

        plan = ProjectPlan(
            plan_id="p1",
            project_name="compat",
            requester="qa",
            actions=[PlanAction(action_id="a1", title="T", instruction="Do it")],
        )
        ids = await engine.execute_plan(plan)
        assert len(ids) == 3  # artifact + status + refined
