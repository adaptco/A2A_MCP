import pytest
from unittest.mock import MagicMock, patch
from agents.coder import CoderAgent
from schemas.database import ArtifactModel

@pytest.mark.asyncio
async def test_generate_solution_handles_empty_parent_context():
    # Mock DBManager
    with patch("agents.coder.DBManager") as MockDBManager:
        mock_db_instance = MockDBManager.return_value
        # Configure get_artifact to return None
        mock_db_instance.get_artifact.return_value = None

        # Mock LLMService
        with patch("agents.coder.LLMService") as MockLLMService:
            mock_llm_instance = MockLLMService.return_value
            mock_llm_instance.call_llm.return_value = "def solution(): pass"

            agent = CoderAgent()

            # Call generate_solution with a dummy parent_id
            artifact = await agent.generate_solution("dummy_parent_id")

            # Verify that get_artifact was called
            mock_db_instance.get_artifact.assert_called_once_with("dummy_parent_id")

            # Verify that call_llm was called with the fallback context content
            expected_prompt_start = "Context: No previous context found. Proceeding with initial architectural build."
            args, _ = mock_llm_instance.call_llm.call_args
            assert args[0].startswith(expected_prompt_start)

            # Verify that save_artifact was called
            mock_db_instance.save_artifact.assert_called_once()
            assert artifact.content == "def solution(): pass"

@pytest.mark.asyncio
async def test_generate_solution_handles_existing_parent_context():
    # Mock DBManager
    with patch("agents.coder.DBManager") as MockDBManager:
        mock_db_instance = MockDBManager.return_value
        # Configure get_artifact to return a valid artifact
        mock_parent_artifact = MagicMock(spec=ArtifactModel)
        mock_parent_artifact.content = "Existing context content"
        mock_db_instance.get_artifact.return_value = mock_parent_artifact

        # Mock LLMService
        with patch("agents.coder.LLMService") as MockLLMService:
            mock_llm_instance = MockLLMService.return_value
            mock_llm_instance.call_llm.return_value = "def solution(): pass"

            agent = CoderAgent()

            # Call generate_solution with a dummy parent_id
            artifact = await agent.generate_solution("dummy_parent_id")

            # Verify that get_artifact was called
            mock_db_instance.get_artifact.assert_called_once_with("dummy_parent_id")

            # Verify that call_llm was called with the existing context content
            expected_prompt_start = "Context: Existing context content"
            args, _ = mock_llm_instance.call_llm.call_args
            assert args[0].startswith(expected_prompt_start)

            # Verify that save_artifact was called
            mock_db_instance.save_artifact.assert_called_once()
