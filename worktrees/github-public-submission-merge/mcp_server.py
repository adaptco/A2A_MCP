from bootstrap import bootstrap_paths

bootstrap_paths()

try:
    from fastmcp import FastMCP
except ModuleNotFoundError:
    from mcp.server.fastmcp import FastMCP
from orchestrator.storage import SessionLocal
from schemas.database import ArtifactModel

# Initialize FastMCP Server
mcp = FastMCP("A2A_Orchestrator")

@mcp.tool()
def get_artifact_trace(root_id: str):
    """Retrieves the full Research -> Code -> Test trace for a specific run."""
    db = SessionLocal()
    try:
        artifacts = db.query(ArtifactModel).filter(
            (ArtifactModel.id == root_id) | (ArtifactModel.parent_artifact_id == root_id)
        ).all()
        return [f"{a.agent_name}: {a.type} (ID: {a.id})" for a in artifacts]
    finally:
        db.close()

@mcp.tool()
def trigger_new_research(query: str):
    """Triggers the A2A pipeline for a new user query via the orchestrator."""
    import requests
    response = requests.post("http://localhost:8000/orchestrate", params={"user_query": query})
    return response.json()

@mcp.tool()
async def launch_game_instance(server_url: str = "ws://localhost:8080", simulate_fallback: bool = False):
    """
    Launches a standalone Jurassic Pixels game instance and returns the artifact.
    Args:
        server_url: WebSocket URL of the game server.
        simulate_fallback: If True, allow falling back to simulation if connection fails.
    """
    from jurassic_pixels.launcher import launch_game
    # Note: launcher.launch_game doesn't accept simulate arg directly in original design, 
    # but speed_runner does. We need to check which launcher is being used.
    # The previous step implemented 'launcher.py' which launches the game.
    # Wait, 'launcher.py' connects to the game. 'speed_runner.py' is the agent.
    # The user wanted to "launch the game".
    
    # If using 'launcher.py' as implemented in Step 1042:
    # It does NOT have simulation logic. It connects to the server to trigger a game.
    # BUT, we also have 'speed_runner.py' which IS an agent that connects to the game.
    
    # Let's verify what launcher.py does.
    # If Docker is down, launcher.py will fail to connect.
    # We should update launcher.py to handle simulation or just return a mock artifact if fallback is requested.
    
    if simulate_fallback:
         # Check if server is reachable, if not return mock
         import asyncio
         try:
             # Fast check
             from jurassic_pixels.launcher import launch_game
             result = await launch_game(server_url)
             if "error" in result:
                 raise Exception(result["error"])
             return result
         except Exception:
             import uuid
             import random
             return {
                "artifact_id": str(uuid.uuid4()),
                "type": "game_instance",
                "content": "Game Instance (Simulated Fallback)",
                "metadata": {
                    "session_id": f"sim-{random.randint(1000,9999)}",
                    "status": "simulated_started",
                    "note": "Real game server unreachable, using simulation."
                }
            }

    from jurassic_pixels.launcher import launch_game
    return await launch_game(server_url)

if __name__ == "__main__":
    mcp.run()
