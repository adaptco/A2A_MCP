from mcp.server.fastmcp import FastMCP
from orchestrator.storage import DBManager
from schemas.database import ArtifactModel

# Initialize FastMCP Server
mcp = FastMCP("A2A_Orchestrator")
db_manager = DBManager()

@mcp.tool()
def get_artifact_trace(root_id: str):
    """Retrieves the full Research -> Code -> Test trace for a specific run."""
    db = db_manager.SessionLocal()
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

if __name__ == "__main__":
    mcp.run()
