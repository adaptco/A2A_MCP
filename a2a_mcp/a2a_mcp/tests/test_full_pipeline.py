# tests/test_full_pipeline.py
"""
End-to-end test for the full 5-agent IntentEngine pipeline:
ManagingAgent → OrchestrationAgent → ArchitectureAgent → CoderAgent → TesterAgent.
"""
from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock

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
        engine = IntentEngine()

        # ── Mock ManagingAgent LLM ──────────────────────────────────
        engine.manager.llm = MagicMock()
        engine.manager.llm.call_llm.return_value = llm_categorisation
        engine.manager.db = MagicMock()

        # ── Mock OrchestrationAgent DB ──────────────────────────────
        engine.orchestrator.db = MagicMock()

        # ── Mock ArchitectureAgent DB (keep real PINN) ──────────────
        engine.architect.db = MagicMock()

        # ── Mock CoderAgent ─────────────────────────────────────────
        engine.coder.llm = MagicMock()
        engine.coder.llm.call_llm.return_value = llm_code
        engine.coder.db = MagicMock()
        engine.coder.db.get_artifact.return_value = None  # no parent context

        # ── Mock TesterAgent ────────────────────────────────────────
        if test_verdicts is None:
            test_verdicts = ["PASS"]

        async def fake_validate(_artifact_id, supplemental_context=None, context_tokens=None):
            verdict = test_verdicts.pop(0) if test_verdicts else "PASS"
            return TestReport(
                status=verdict,
                critique="All clear" if verdict == "PASS" else "Bug found",
            )

        engine.tester.validate = fake_validate  # type: ignore[assignment]

        # ── Mock top-level DB ───────────────────────────────────────
        engine.db = MagicMock()

        return engine

    # -----------------------------------------------------------------
    # Happy-path: every agent succeeds on the first try
    # -----------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_happy_path_all_pass(self):
        engine = self._make_engine()
        result = await engine.run_full_pipeline("Build a user service")

        assert isinstance(result, PipelineResult)
        assert result.success is True

        # ManagingAgent produced a plan with actions
        assert len(result.plan.actions) > 0

        # OrchestrationAgent produced a blueprint
        assert result.blueprint.plan_id.startswith("blueprint-")

        # ArchitectureAgent produced architecture artifacts
        assert len(result.architecture_artifacts) > 0
        assert all(a.type == "architecture_doc" for a in result.architecture_artifacts)

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

        result = await engine.run_full_pipeline("Build something")

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

        result = await engine.run_full_pipeline(
            "Doomed project", max_healing_retries=2
        )

        assert result.success is False
        # All blueprint actions should be marked "failed"
        assert all(a.status == "failed" for a in result.blueprint.actions)

    # -----------------------------------------------------------------
    # Pipeline result contains correct artefact counts
    # -----------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_artifact_counts(self):
        engine = self._make_engine(
            llm_categorisation="1. Task A",  # 1 task → 4 pipeline stages
        )
        result = await engine.run_full_pipeline("Single task project")

        # blueprint actions = 1 task × 4 pipeline stages
        assert len(result.blueprint.actions) == 4

        # architecture artifacts = one per blueprint action
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
