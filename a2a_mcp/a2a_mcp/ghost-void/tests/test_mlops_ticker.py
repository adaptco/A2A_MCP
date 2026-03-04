import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from middleware.events import PostgresEventStore
from middleware.observers.whatsapp import WhatsAppEventObserver
from schemas.model_artifact import ModelArtifact, AgentLifecycleState

@pytest.mark.asyncio
class TestMLOpsTicker:
    async def test_event_store_terminal_filtering(self):
        """Verify that only terminal events trigger observers."""
        # Use MagicMock with AsyncMock method for on_state_change
        mock_observer = MagicMock()
        mock_observer.on_state_change = AsyncMock()
        
        mock_db = MagicMock()
        # Mock save to return input
        mock_db.save_artifact.side_effect = lambda x: x
        
        # Patch the module-level _db_manager in middleware.events
        with patch("middleware.events._db_manager", mock_db):
            store = PostgresEventStore(observers=[mock_observer])
            
            # 1. INIT -> No notification
            artifact_init = ModelArtifact(
                artifact_id="init-1",
                model_id="test",
                weights_hash="h1",
                embedding_dim=1,
                state=AgentLifecycleState.INIT,
                content="test"
            )
            await store.append_event(artifact_init)
            mock_observer.on_state_change.assert_not_called()
            
            # 2. Terminal state (DIRECT SET for testing filtering)
            # We bypass transition check to test the filtering logic independently
            artifact_converged = artifact_init.model_copy(update={"state": AgentLifecycleState.CONVERGED})
            await store.append_event(artifact_converged)
            
            # Verify call
            mock_observer.on_state_change.assert_called_once()
            args = mock_observer.on_state_change.call_args[0]
            assert args[0].state == AgentLifecycleState.CONVERGED

    async def test_whatsapp_message_format(self):
        """Verify WhatsApp message formatting."""
        observer = WhatsAppEventObserver(channel_id="123", api_token="abc")
        
        artifact = ModelArtifact(
            artifact_id="verify-1",
            model_id="test-model",
            weights_hash="ver-hash-1234567890",
            embedding_dim=10,
            state=AgentLifecycleState.CONVERGED,
            content="verification content",
            metadata={"pipeline_id": "pip-1", "execution_id": "exec-1"}
        )
        
        body = observer._format_message(artifact)
        assert "[MODEL EVENT VERIFIED]" in body
        assert "pipeline: pip-1" in body
        assert "execution: exec-1" in body
        assert "state: CONVERGED" in body
        assert "hash: ver-hash-123..." in body

    @patch("httpx.AsyncClient")
    async def test_whatsapp_send_success(self, mock_client_cls):
        """Verify WhatsApp sending logic."""
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        
        # Configure raise_for_status mock
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_response
        
        observer = WhatsAppEventObserver(channel_id="123", api_token="abc")
        artifact = ModelArtifact(
            artifact_id="send-1",
            model_id="test",
            weights_hash="hash",
            embedding_dim=1,
            state=AgentLifecycleState.FAILED,
            content="failed"
        )
        
        await observer.on_state_change(artifact)
        
        mock_client.post.assert_called_once()
        args, kwargs = mock_client.post.call_args
        assert kwargs["json"]["to"] == "123"
        assert "FAILED" in kwargs["json"]["text"]["body"]
