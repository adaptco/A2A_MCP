
import asyncio
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from schemas import ModelArtifact, AgentLifecycleState, LoRAConfig

# --- Application Setup ---
app = FastAPI(
    title="A2A_MCP Agent Simulator",
    description="Simulates the agent lifecycle for LoRA adaptation.",
)

# In-memory database to store our model artifacts
DB = {}

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# --- Background Task for State Transitions ---
async def advance_lifecycle(artifact_id: str):
    """A mock background task to simulate the agent's lifecycle progression."""
    artifact = DB.get(artifact_id)
    if not artifact:
        return

    # 1. EMBEDDING -> RAG_QUERY
    await asyncio.sleep(2)  # Simulate work
    artifact.state = AgentLifecycleState.RAG_QUERY
    print(f"Agent {artifact_id}: State transitioned to {artifact.state}")

    # 2. RAG_QUERY -> LORA_ADAPT
    await asyncio.sleep(3)  # Simulate RAG query and data gathering
    artifact.state = AgentLifecycleState.LORA_ADAPT
    # Attach a default LoRA config before training
    artifact.lora_config = LoRAConfig(training_samples=1500)
    print(f"Agent {artifact_id}: State transitioned to {artifact.state}")

    # 3. LORA_ADAPT -> TRAINED
    await asyncio.sleep(5)  # Simulate the LoRA training job
    artifact.state = AgentLifecycleState.TRAINED
    print(f"Agent {artifact_id}: State transitioned to {artifact.state}. Adaptation complete.")


# --- API Endpoints ---

@app.get("/", response_class=HTMLResponse)
async def get_frontend(request: Request):
    """Serves the main frontend page."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/agents", response_model=ModelArtifact, status_code=201)
async def create_agent():
    """Creates a new model artifact and puts it in the EMBEDDING state."""
    # Create a new artifact in the initial state
    artifact = ModelArtifact(state=AgentLifecycleState.INITIAL)
    
    # Transition to the first active state
    artifact.state = AgentLifecycleState.EMBEDDING
    
    # Store it in our "database"
    DB[artifact.artifact_id] = artifact
    print(f"Created Agent: {artifact.artifact_id} in state {artifact.state}")
    
    return artifact


@app.get("/agents/{artifact_id}", response_model=ModelArtifact)
async def get_agent_status(artifact_id: str):
    """Retrieves the current status of a model artifact."""
    artifact = DB.get(artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Agent artifact not found.")
    return artifact


@app.post("/agents/{artifact_id}/adapt", response_model=ModelArtifact)
async def start_lora_adaptation(artifact_id: str, request: Request):
    """Triggers the LoRA adaptation lifecycle for an agent."""
    artifact = DB.get(artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Agent artifact not found.")

    if artifact.state != AgentLifecycleState.EMBEDDING:
        raise HTTPException(
            status_code=400,
            detail=f"Agent must be in EMBEDDING state to start adaptation, but is in {artifact.state}."
        )

    # Run the lifecycle progression in the background
    asyncio.create_task(advance_lifecycle(artifact_id))

    return artifact
