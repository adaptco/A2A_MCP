import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, ANY
from agency_hub.genie_bridge import GenieBridge
from middleware.genie_adapter import GenieAdapter
from middleware.runtime import AgenticRuntime
from schemas.model_artifact import ModelArtifact, AgentLifecycleState

@pytest.fixture
def mock_spoke():
    spoke = MagicMock()
    spoke.act.return_value = True
    spoke.observe.return_value = {
        "passability": {"up": True, "down": True},
        "entities": [{"type": "pixel_tree", "x": 10, "y": 20}],
        "timestamp": 123456789
    }
    return spoke

@pytest.fixture
def mock_runtime():
    runtime = MagicMock(spec=AgenticRuntime)
    runtime.emit_event = AsyncMock()
    return runtime

@pytest.mark.asyncio
async def test_genie_interactive_loop(mock_spoke, mock_runtime):
    # Setup
    bridge = GenieBridge(mock_spoke)
    adapter = GenieAdapter(mock_runtime, bridge)
    
    # 1. Start Session
    await adapter.start_interactive_session()
    mock_runtime.emit_event.assert_called_with(ANY)
    
    # 2. Process WASD Input ('w' for up)
    payload = {"intent": "w"}
    response = await adapter.process_client_input(payload)
    
    # 3. Verify Translation
    mock_spoke.act.assert_called_with({"action": "move", "params": {"direction": "up", "magnitude": 1.0}})
    
    # 4. Verify Projection
    assert response["success"] is True
    assert response["projection"]["last_intent"] == "w"
    assert len(response["projection"]["nearby_entities"]) == 1
    
    # 5. Verify Artifact Trace
    # Check that emit_event was called for the action
    assert mock_runtime.emit_event.call_count == 2
    last_call_artifact = mock_runtime.emit_event.call_args[0][0]
    assert "genie-act-w" in last_call_artifact.artifact_id
    assert last_call_artifact.state == AgentLifecycleState.INIT

@pytest.mark.asyncio
async def test_genie_unsupported_intent(mock_spoke, mock_runtime):
    bridge = GenieBridge(mock_spoke)
    adapter = GenieAdapter(mock_runtime, bridge)
    adapter.is_active = True
    
    payload = {"intent": "xyz"} # Invalid
    response = await adapter.process_client_input(payload)
    
    assert response["success"] is False # Success of handling is false
    mock_spoke.act.assert_not_called()
