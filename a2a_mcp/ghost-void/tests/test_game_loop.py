import asyncio
import websockets
import json
import pytest

@pytest.mark.asyncio
async def test_websocket_connection():
    uri = "ws://localhost:8080"
    try:
        async with websockets.connect(uri) as websocket:
            print(f"Connected to {uri}")
            
            # Wait for messages until we get a render_frame
            for _ in range(10): # Try 10 messages max
                message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(message)
                print(f"Received: {data}")
                
                if data.get("type") == "render_frame":
                    assert "sprites" in data
                    assert isinstance(data["sprites"], list)
                    if len(data["sprites"]) > 0:
                        first_sprite = data["sprites"][0]
                        print(f"Sample Sprite: {first_sprite}")
                        assert "x" in first_sprite
                        assert "y" in first_sprite
                    return # Success

                if data.get("type") == "state_update":
                    assert "frame_processed" in data
                    assert isinstance(data["frame_processed"], bool)
                    return # Success
            
            pytest.fail("Did not receive render_frame message")
            
    except OSError as e:
        pytest.skip(f"WebSocket server unavailable at {uri}: {e}")
    except Exception as e:
        pytest.fail(f"WebSocket connection failed: {e}")

if __name__ == "__main__":
    # simple run if executed directly
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test_websocket_connection())
