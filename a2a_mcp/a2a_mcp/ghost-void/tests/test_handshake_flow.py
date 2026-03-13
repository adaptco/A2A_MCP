
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from middleware import AgenticRuntime
from agency_hub.docking_shell import DockingShell
from schemas.model_artifact import ModelArtifact, AgentLifecycleState

@pytest.mark.asyncio
async def test_handshake_initiation_and_transition():
    """Verify that initiate_handshake creates a HANDSHAKE event and can transition to INIT."""
    mock_db = MagicMock()
    mock_db.save_artifact.side_effect = lambda x: x
    
    with patch("middleware.events._db_manager", mock_db):
        runtime = AgenticRuntime()
        
        # 1. Initiate Handshake
        handshake_art = await runtime.initiate_handshake(
            model_id="avatar-v1",
            weights_hash="hash123",
            embedding_dim=128,
            metadata={"source": "client-llm"}
        )
        
        assert handshake_art.state == AgentLifecycleState.HANDSHAKE
        assert handshake_art.model_id == "avatar-v1"
        assert handshake_art.metadata["source"] == "client-llm"
        mock_db.save_artifact.assert_called_once()
        
        # 2. Transition to INIT (handshake -> onboarding)
        init_art = await runtime.transition_and_emit(handshake_art, AgentLifecycleState.INIT)
        assert init_art.state == AgentLifecycleState.INIT
        assert init_art.parent_artifact_id == handshake_art.artifact_id

@pytest.mark.asyncio
async def test_docking_shell_handshake_integration():
    """Verify that DockingShell triggers a handshake during docking if runtime is provided."""
    mock_runtime = MagicMock(spec=AgenticRuntime)
    mock_runtime.initiate_handshake = AsyncMock()
    
    shell = DockingShell(runtime=mock_runtime)
    mock_spoke = MagicMock()
    
    model_info = {
        "model_id": "test-model",
        "weights_hash": "w123",
        "embedding_dim": 64,
        "metadata": {"user": "tester"}
    }
    
    await shell.dock(mock_spoke, model_info=model_info)
    
    assert shell.spoke == mock_spoke
    mock_runtime.initiate_handshake.assert_called_once_with(
        model_id="test-model",
        weights_hash="w123",
        embedding_dim=64,
        metadata={"user": "tester"}
    )
