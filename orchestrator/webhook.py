import logging
import time
from fastapi import FastAPI, HTTPException, Body, Response, APIRouter, Depends
from prometheus_client import generate_latest, REGISTRY
from orchestrator.stateflow import StateMachine, State
from orchestrator.storage import save_plan_state
from orchestrator.intent_engine import IntentEngine
from orchestrator.utils import extract_plan_id_from_path
from orchestrator.verify_api import router as verify_router
from orchestrator.auth import authenticate_user

logger = logging.getLogger(__name__)

app = FastAPI(title="A2A MCP Webhook")
app.include_router(verify_router)

ingress_router = APIRouter()

# in-memory map
PLAN_STATE_MACHINES = {}

def persistence_callback(plan_id: str, state_dict: dict) -> None:
    """Callback to persist FSM state to database."""
    try:
        save_plan_state(plan_id, state_dict)
    except Exception as e:
        logger.warning(f"Failed to persist plan state for {plan_id}: {e}")

def _register_executing_callback(sm: StateMachine, engine: Any):
    # Logic to trigger actual agent processing when state enters EXECUTING
    pass

def _resolve_plan_id(path_plan_id: str | None, payload: dict) -> str | None:
    if path_plan_id: return path_plan_id.strip()
    plan_id = payload.get("plan_id")
    if plan_id: return str(plan_id).strip()
    extracted = extract_plan_id_from_path(payload.get("plan_file_path", ""))
    return extracted.strip() if extracted else None

async def _plan_ingress_impl(path_plan_id: str | None, payload: dict):
    plan_id = _resolve_plan_id(path_plan_id, payload or {})
    if not plan_id:
        raise HTTPException(status_code=400, detail="Unable to determine plan_id")

    sm = PLAN_STATE_MACHINES.get(plan_id)
    if not sm:
        sm = StateMachine(max_retries=3, persistence_callback=persistence_callback)
        sm.plan_id = plan_id
        _register_executing_callback(sm, sm)
        PLAN_STATE_MACHINES[plan_id] = sm

    rec = sm.trigger("OBJECTIVE_INGRESS")
    return {"status": "scheduled", "plan_id": plan_id, "transition": rec.to_dict()}

@ingress_router.post("/plans/ingress")
async def plan_ingress(payload: dict = Body(...)):
    return await _plan_ingress_impl(None, payload)

@ingress_router.post("/plans/{plan_id}/ingress")
async def plan_ingress_by_id(plan_id: str, payload: dict = Body(default={})):
    return await _plan_ingress_impl(plan_id, payload)

@app.post("/orchestrate")
async def orchestrate(user_query: str):
    engine = IntentEngine()
    try:
        result = await engine.run_full_pipeline(description=user_query, requester="api_user")
        return {
            "status": "A2A Workflow Complete",
            "success": result.success,
            "pipeline_results": {
                "plan_id": result.plan.plan_id,
                "code_artifacts": [a.artifact_id for a in result.code_artifacts],
            },
            "final_code": result.code_artifacts[-1].content if result.code_artifacts else None,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics")
def metrics():
    return Response(content=generate_latest(REGISTRY), media_type="text/plain; version=0.0.4")

app.include_router(ingress_router)
