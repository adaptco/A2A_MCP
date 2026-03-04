"""
Tests for Challenge Generator service.
"""
import pytest
from unittest.mock import Mock, MagicMock
from schemas import SemanticChallenge
from challenge_generator import ChallengeGenerator

class TestChallengeGenerator:
    """Test AI challenge generation logic."""
    
    @pytest.fixture
    def mock_qdrant(self):
        """Mock Qdrant client."""
        client = Mock()
        
        # Mock focus tool retrieval
        focus_point = MagicMock()
        focus_point.id = "grep_001"
        focus_point.vector = [0.1] * 768
        focus_point.payload = {
            "tool_name": "grep",
            "description": "Global Regular Expression Print",
            "difficulty_tier": 2
        }
        
        # Mock neighbors
        neighbor_point = MagicMock()
        neighbor_point.id = "awk_001"
        neighbor_point.score = 0.85
        neighbor_point.payload = {
            "tool_name": "awk",
            "description": "Pattern scanning"
        }
        
        client.retrieve.return_value = [focus_point]
        client.search.return_value = [focus_point, neighbor_point]
        
        return client

    def test_generate_challenge(self, mock_qdrant):
        """Test basic challenge generation."""
        generator = ChallengeGenerator(mock_qdrant, "test_collection")
        
        challenge = generator.generate_challenge("grep_001")
        
        assert isinstance(challenge, SemanticChallenge)
        assert challenge.challenge_id.startswith("ch_grep_001")
        assert "grep" in challenge.required_tools
        assert "awk" in challenge.semantic_neighbors
        assert challenge.xp_reward > 0
        
        # Verify interactions
        mock_qdrant.retrieve.assert_called_once()
        mock_qdrant.search.assert_called_once()

    def test_tool_not_found(self, mock_qdrant):
        """Test handling of missing tools."""
        mock_qdrant.retrieve.return_value = []
        
        generator = ChallengeGenerator(mock_qdrant, "test_collection")
        challenge = generator.generate_challenge("missing_tool")
        
        assert challenge is None

if __name__ == "__main__":
    # Allow running directly
    pytest.main([__file__, "-v"])
