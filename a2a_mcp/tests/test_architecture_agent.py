# tests/test_architecture_agent.py
"""Unit tests for the ArchitectureAgent."""
from unittest.mock import MagicMock

import pytest

from agents.architecture_agent import ArchitectureAgent
from schemas.project_plan import PlanAction, ProjectPlan


class TestArchitectureAgent:
    """Tests for ArchitectureAgent.map_system()."""

    def _make_agent(self) -> ArchitectureAgent:
        agent = ArchitectureAgent()
        agent.db = MagicMock()
        # Keep the real PINN agent (deterministic embedding, no network calls)
        return agent

    def _simple_plan(self) -> ProjectPlan:
        return ProjectPlan(
            plan_id="test-plan-001",
            project_name="Test System",
            requester="qa",
            actions=[
                PlanAction(action_id="a1", title="Auth Module", instruction="Build auth"),
                PlanAction(action_id="a2", title="DB Layer", instruction="Build db"),
            ],
        )

    @pytest.mark.asyncio
    async def test_map_system_returns_artifacts(self):
        agent = self._make_agent()
        plan = self._simple_plan()

        artifacts = await agent.map_system(plan)

        assert len(artifacts) == 2
        assert all(a.type == "architecture_doc" for a in artifacts)

    @pytest.mark.asyncio
    async def test_map_system_records_in_world_model(self):
        agent = self._make_agent()
        plan = self._simple_plan()

        await agent.map_system(plan)

        # PINN world model should now contain vector tokens
        wm = agent.pinn.world_model
        assert len(wm.vector_tokens) == 2
        # And the knowledge graph should link plan → artifacts
        assert plan.plan_id in wm.knowledge_graph

    @pytest.mark.asyncio
    async def test_map_system_persists_all_artifacts(self):
        agent = self._make_agent()
        plan = self._simple_plan()

        await agent.map_system(plan)

        assert agent.db.save_artifact.call_count == 2
