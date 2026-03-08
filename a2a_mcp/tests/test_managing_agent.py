# tests/test_managing_agent.py
"""Unit tests for the ManagingAgent."""
import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from agents.managing_agent import ManagingAgent
from schemas.project_plan import ProjectPlan


class TestManagingAgent:
    """Tests for ManagingAgent.categorize_project()."""

    def _make_agent_with_mocked_llm(self, llm_response: str) -> ManagingAgent:
        agent = ManagingAgent()
        agent.llm = MagicMock()
        agent.llm.call_llm.return_value = llm_response
        agent.db = MagicMock()
        return agent

    @pytest.mark.asyncio
    async def test_categorize_produces_plan(self):
        llm_text = (
            "1. Design the database schema\n"
            "2. Implement the REST API\n"
            "3. Write integration tests\n"
        )
        agent = self._make_agent_with_mocked_llm(llm_text)

        plan = await agent.categorize_project("Build a user management service")

        assert isinstance(plan, ProjectPlan)
        assert plan.plan_id.startswith("plan-")
        assert len(plan.actions) == 3
        assert plan.actions[0].status == "pending"

    @pytest.mark.asyncio
    async def test_categorize_persists_artifact(self):
        agent = self._make_agent_with_mocked_llm("1. Do something")
        await agent.categorize_project("Demo")

        agent.db.save_artifact.assert_called_once()

    @pytest.mark.asyncio
    async def test_categorize_fallback_single_action(self):
        """When the LLM returns un-parseable text, a catch-all action is created."""
        agent = self._make_agent_with_mocked_llm("")
        plan = await agent.categorize_project("Vague request")

        assert len(plan.actions) == 1
        assert plan.actions[0].title == "Catch-all task"

    @pytest.mark.asyncio
    async def test_parse_actions_handles_varied_formats(self):
        """Verify the parser handles '1.', '1)', and '- ' prefixes."""
        lines = "1. First\n2) Second\n- Third"
        actions = ManagingAgent._parse_actions(lines)
        assert len(actions) == 3
