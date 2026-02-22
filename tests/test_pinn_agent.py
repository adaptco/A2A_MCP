import pytest
from unittest.mock import MagicMock, patch
from agents.pinn_agent import PINNAgent
from schemas.world_model import VectorToken, WorldModel

class TestPINNAgent:

    @pytest.fixture
    def pinn_agent(self):
        """Fixture to initialize PINNAgent with mocked LLMService."""
        with patch("agents.pinn_agent.LLMService"):
            yield PINNAgent()

    def test_initialization(self, pinn_agent):
        """Test that PINNAgent initializes correctly."""
        assert pinn_agent.agent_name == "PINNAgent-Alpha"
        assert pinn_agent.llm is not None
        assert isinstance(pinn_agent.world_model, WorldModel)

    def test_deterministic_embedding_consistency(self, pinn_agent):
        """Test that deterministic embedding produces consistent results."""
        text = "Hello World"
        embedding1 = pinn_agent._deterministic_embedding(text)
        embedding2 = pinn_agent._deterministic_embedding(text)
        assert embedding1 == embedding2

    def test_deterministic_embedding_format(self, pinn_agent):
        """Test the format of the deterministic embedding."""
        text = "Test Content"
        embedding = pinn_agent._deterministic_embedding(text)
        assert isinstance(embedding, list)
        assert len(embedding) == 16
        assert all(isinstance(val, float) for val in embedding)

    def test_rank_prompt_calls_llm(self, pinn_agent):
        """Test that rank_prompt calls LLMService but returns deterministic embedding."""
        prompt_text = "Analyze this"
        # Setup mock to return something (even though it's ignored)
        pinn_agent.llm.call_llm.return_value = "Ignored Response"

        result = pinn_agent.rank_prompt(prompt_text)

        # Verify LLM call
        pinn_agent.llm.call_llm.assert_called_once_with(
            prompt=f"Return only an embedding for: {prompt_text}",
            system_prompt="You are an embedding helper."
        )

        # Verify it falls back/uses deterministic embedding
        expected_embedding = pinn_agent._deterministic_embedding(prompt_text)
        assert result == expected_embedding

    def test_rank_prompt_fallback_on_error(self, pinn_agent):
        """Test fallback to deterministic embedding when LLM fails."""
        prompt_text = "Failure case"
        pinn_agent.llm.call_llm.side_effect = Exception("LLM Error")

        result = pinn_agent.rank_prompt(prompt_text)

        # Verify fallback
        expected_embedding = pinn_agent._deterministic_embedding(prompt_text)
        assert result == expected_embedding

    def test_ingest_artifact_creates_token(self, pinn_agent):
        """Test that ingest_artifact creates a VectorToken and adds it to the world model."""
        artifact_id = "art-001"
        content = "Important knowledge"

        # We can rely on deterministic embedding, or spy on rank_prompt if needed.
        # Here we just verify the outcome.

        token = pinn_agent.ingest_artifact(artifact_id, content)

        # Verify token properties
        assert isinstance(token, VectorToken)
        assert token.source_artifact_id == artifact_id
        assert token.text == content
        assert len(token.vector) == 16

        # Verify it's in the world model
        assert token.token_id in pinn_agent.world_model.vector_tokens
        assert pinn_agent.world_model.vector_tokens[token.token_id] == token

    def test_ingest_artifact_links_parent(self, pinn_agent):
        """Test that ingest_artifact links parent and child in the knowledge graph."""
        parent_id = "parent-123"
        child_id = "child-456"
        content = "Derived content"

        pinn_agent.ingest_artifact(child_id, content, parent_id=parent_id)

        # Verify link in knowledge graph
        assert parent_id in pinn_agent.world_model.knowledge_graph
        assert child_id in pinn_agent.world_model.knowledge_graph[parent_id]
