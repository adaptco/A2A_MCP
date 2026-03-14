import asyncio
import websockets
import json
import uuid
import sys

async def launch_game(server_url: str = "ws://localhost:8080"):
    """
    Connects to the game server and initiates a new game session.
    Returns a dictionary representing the game artifact.
    """
    try:
        async with websockets.connect(server_url) as websocket:
            # Handshake / Init
            init_msg = {
                "type": "init",
                "client_id": str(uuid.uuid4()),
                "role": "launcher"
            }
            await websocket.send(json.dumps(init_msg))
            
            # Wait for ack or game start confirmation
            # For this MVP, we assume connection success implies readiness.
            
            # Request game start
            start_msg = {
                "type": "start_game",
                "mode": "standard"
            }
            await websocket.send(json.dumps(start_msg))
            
            # Receive confirmation (mocked for now as we don't have full server protocol specs)
            response = await websocket.recv()
            data = json.loads(response)
            
            artifact = {
                "artifact_id": str(uuid.uuid4()),
                "type": "game_instance",
                "content": f"Game Instance Launched via {server_url}",
                "metadata": {
                    "server_response": data,
                    "session_id": data.get("session_id", "unknown")
                }
            }
            return artifact

    except Exception as e:
        return {
            "error": str(e),
            "status": "failed"
        }

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "ws://localhost:8080"
    result = asyncio.run(launch_game(url))
    print(json.dumps(result, indent=2))
