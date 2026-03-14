import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from middleware.observers.tetris import TetrisScoreAggregator
from schemas.model_artifact import ModelArtifact, AgentLifecycleState

@pytest.mark.asyncio
class TestTetrisObserver:
    async def test_aggregation_logic(self):
        """Verify that multiple events are aggregated into a single summary."""
        mock_whatsapp = MagicMock()
        mock_whatsapp._send_whatsapp_message = AsyncMock()
        
        # Interval set to 0.1s for fast testing
        aggregator = TetrisScoreAggregator(mock_whatsapp, flush_interval_seconds=0.1)
        
        # Mock gaming events using real ModelArtifact for schema adherence
        event1 = ModelArtifact(
            artifact_id="tetris-1-a",
            model_id="tetris",
            weights_hash="h1",
            embedding_dim=1,
            category="gaming",
            state=AgentLifecycleState.SCORE_FINALIZED,
            content="score",
            metadata={"pipeline_id": "tetris-1", "score": 100}
        )
        
        event2 = ModelArtifact(
            artifact_id="tetris-1-b",
            model_id="tetris",
            weights_hash="h1",
            embedding_dim=1,
            category="gaming",
            state=AgentLifecycleState.SCORE_FINALIZED,
            content="score",
            metadata={"pipeline_id": "tetris-1", "score": 200}
        )
        
        # Trigger events
        await aggregator.on_state_change(event1)
        await aggregator.on_state_change(event2)
        
        assert len(aggregator.buffer) == 2
        
        # Wait for flush
        await asyncio.sleep(0.2)
        
        # Verify flush happened
        assert len(aggregator.buffer) == 0
        mock_whatsapp._send_whatsapp_message.assert_called_once()
        
        summary = mock_whatsapp._send_whatsapp_message.call_args[0][0]
        assert "count: 2 matches" in summary
        assert "avg_score: 150.00" in summary
        assert "high_score: 200" in summary

    async def test_filtering_logic(self):
        """Verify that non-gaming events are ignored."""
        mock_whatsapp = MagicMock()
        mock_whatsapp._send_whatsapp_message = AsyncMock()
        aggregator = TetrisScoreAggregator(mock_whatsapp)
        
        event = ModelArtifact(
            artifact_id="m1",
            model_id="m1",
            weights_hash="h",
            embedding_dim=1,
            category="mlops",
            state=AgentLifecycleState.CONVERGED,
            content="mlops"
        )
        await aggregator.on_state_change(event)
        
        assert len(aggregator.buffer) == 0
