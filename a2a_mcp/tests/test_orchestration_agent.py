# tests/test_orchestration_agent.py
"""Unit tests for the OrchestrationAgent."""
from unittest.mock import MagicMock

import pytest

from agents.orchestration_agent import OrchestrationAgent, AGENT_PIPELINE
from schemas.project_plan import ProjectPlan


class TestOrchestrationAgent:
    """Tests for OrchestrationAgent.build_blueprint()."""

    def _make_agent(self) -> OrchestrationAgent:
        agent = OrchestrationAgent()
        agent.db = MagicMock()
        return agent

    @pytest.mark.asyncio
    async def test_build_blueprint_returns_project_plan(self):
        agent = self._make_agent()
        plan = await agent.build_blueprint(
            project_name="Demo Project",
            task_descriptions=["Build API", "Write tests"],
        )

        assert isinstance(plan, ProjectPlan)
        assert plan.plan_id.startswith("blueprint-")
        assert plan.project_name == "Demo Project"

    @pytest.mark.asyncio
    async def test_blueprint_creates_actions_per_pipeline_stage(self):
        agent = self._make_agent()
        tasks = ["task-alpha"]
        plan = await agent.build_blueprint("P", tasks)

        # One action per pipeline stage per task
        assert len(plan.actions) == len(AGENT_PIPELINE) * len(tasks)

    @pytest.mark.asyncio
    async def test_blueprint_action_metadata_contains_delegation(self):
        agent = self._make_agent()
        plan = await agent.build_blueprint("P", ["Do something"])

        delegated_agents = [a.metadata["delegated_to"] for a in plan.actions]
        assert delegated_agents == list(AGENT_PIPELINE)

    @pytest.mark.asyncio
    async def test_blueprint_persists_artifact(self):
        agent = self._make_agent()
        await agent.build_blueprint("P", ["task"])

        agent.db.save_artifact.assert_called_once()
