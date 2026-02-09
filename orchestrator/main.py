from fastapi import FastAPI, HTTPException
from typing import Dict
import uvicorn

# Import the schema and the actual agents
from schemas.agent_artifacts import MCPArtifact
from agents.researcher import ResearcherAgent
from agents.coder import CoderAgent

app = FastAPI(title="A2A MCP Orchestrator")

# Initialize agents
researcher = ResearcherAgent()
coder = CoderAgent()

# In-memory store for tracking artifact history
artifact_store: Dict[str, MCPArtifact] = {}

@app.post("/orchestrate")
async def orchestrate_flow(user_query: str):
    """
    The Real A2A Flow:
    1. Researcher generates a research_doc artifact.
    2. Coder consumes that artifact to produce a code_solution.
    """
    try:
        # STEP 1: Execute Researcher
        research_artifact = await researcher.run(topic=user_query)
        artifact_store[research_artifact.artifact_id] = research_artifact

        # STEP 2: Pass Researcher's output directly to the Coder
        coding_artifact = await coder.run(research_artifact=research_artifact)
        artifact_store[coding_artifact.artifact_id] = coding_artifact

        return {
            "status": "A2A Pipeline Complete",
            "research_id": research_artifact.artifact_id,
            "coder_id": coding_artifact.artifact_id,
            "final_code": coding_artifact.content
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"A2A Pipeline Failed: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
