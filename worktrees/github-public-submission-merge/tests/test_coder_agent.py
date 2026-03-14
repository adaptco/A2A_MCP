import pytest
from unittest.mock import MagicMock
from agents.coder import CoderAgent
from schemas.agent_artifacts import MCPArtifact

class TestCoderAgent:

    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    @pytest.fixture
    def mock_llm(self):
        return MagicMock()

    @pytest.fixture
    def coder_agent(self, mock_db, mock_llm):
        agent = CoderAgent()
        agent.db = mock_db
        agent.llm = mock_llm
        return agent

    @pytest.mark.asyncio
    async def test_generate_solution_success(self, coder_agent, mock_db, mock_llm):
        parent_id = "parent-123"
        feedback = "Please optimize."

        # Mock DB get_artifact
        mock_artifact = MagicMock()
        mock_artifact.content = "Existing code context"
        mock_db.get_artifact.return_value = mock_artifact

        # Mock LLM response
        mock_llm.call_llm.return_value = "def optimize(): pass"

        result = await coder_agent.generate_solution(parent_id, feedback)

        # Verify DB get_artifact called
        mock_db.get_artifact.assert_called_once_with(parent_id)

        # Verify LLM call
        expected_prompt = f"Context: Existing code context\nFeedback: {feedback}"
        mock_llm.call_llm.assert_called_once_with(expected_prompt)

        # Verify result structure
        assert isinstance(result, MCPArtifact)
        assert result.content == "def optimize(): pass"
        assert result.parent_artifact_id == parent_id
        assert result.type == "code_solution"

        # Verify DB save_artifact called
        mock_db.save_artifact.assert_called_once()
        saved_artifact = mock_db.save_artifact.call_args[0][0]
        assert saved_artifact.content == "def optimize(): pass"

    @pytest.mark.asyncio
    async def test_generate_solution_no_context(self, coder_agent, mock_db, mock_llm):
        parent_id = "parent-456"

        # Mock DB get_artifact returning None
        mock_db.get_artifact.return_value = None

        # Mock LLM response
        mock_llm.call_llm.return_value = "def initial(): pass"

        result = await coder_agent.generate_solution(parent_id)

        # Verify correct prompt for missing context
        expected_context = "No previous context found. Proceeding with initial architectural build."
        expected_prompt = f"Context: {expected_context}\nFeedback: Initial build"
        mock_llm.call_llm.assert_called_once_with(expected_prompt)

        assert result.content == "def initial(): pass"

    @pytest.mark.asyncio
    async def test_generate_solution_with_feedback(self, coder_agent, mock_db, mock_llm):
        parent_id = "parent-789"
        feedback = "Add comments."

        # Mock DB get_artifact
        mock_artifact = MagicMock()
        mock_artifact.content = "Some code"
        mock_db.get_artifact.return_value = mock_artifact

        mock_llm.call_llm.return_value = "# Commented code"

        await coder_agent.generate_solution(parent_id, feedback)

        expected_prompt = f"Context: Some code\nFeedback: {feedback}"
        mock_llm.call_llm.assert_called_once_with(expected_prompt)
