import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import json
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from jurassic_pixels.launcher import launch_game

@pytest.mark.asyncio
async def test_launch_game_success():
    # Mock authentication and game start sequence
    mock_websocket = AsyncMock()
    # First recv for connection ack (optional), second for game start response
    mock_websocket.recv.side_effect = [
        json.dumps({"session_id": "test-session-123", "status": "started"})
    ]
    
    # Mock the context manager response
    mock_connect_cm = AsyncMock()
    mock_connect_cm.__aenter__.return_value = mock_websocket
    
    with patch("websockets.connect", return_value=mock_connect_cm):
        result = await launch_game("ws://test:8080")
        
        # Check if we got an error
        if "error" in result:
            pytest.fail(f"Launcher returned error: {result['error']}")

        assert result["type"] == "game_instance"
        assert result["metadata"]["session_id"] == "test-session-123"
        
        # Verify init and start messages sent
        assert mock_websocket.send.call_count == 2

@pytest.mark.asyncio
async def test_launch_game_failure():
    with patch("websockets.connect", side_effect=Exception("Connection refused")):
        result = await launch_game("ws://bad-url:8080")
        assert result["status"] == "failed"
        assert "Connection refused" in result["error"]
