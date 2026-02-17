from fastapi import FastAPI, HTTPException, Body
from orchestrator.stateflow import StateMachine
from orchestrator.utils import extract_plan_id_from_path
<<<<<<< HEAD
from orchestrator.verify_api import router as verify_router

app = FastAPI(title="A2A MCP Webhook")
app.include_router(verify_router)
=======
from orchestrator.storage import save_plan_state
from orchestrator.intent_engine import IntentEngine

app = FastAPI(title="A2A MCP Webhook")
>>>>>>> cde431b91765a0efa58a544c6bbce7e87c940fbe

# in-memory map (replace with DB-backed persistence or plan state store in prod)
PLAN_STATE_MACHINES = {}

<<<<<<< HEAD
=======
def persistence_callback(plan_id: str, state_dict: dict) -> None:
    """Callback to persist FSM state to database."""
    try:
        save_plan_state(plan_id, state_dict)
    except Exception as e:
        print(f"Warning: Failed to persist plan state for {plan_id}: {e}")

>>>>>>> cde431b91765a0efa58a544c6bbce7e87c940fbe

def _resolve_plan_id(path_plan_id: str | None, payload: dict) -> str | None:
    if path_plan_id:
        return path_plan_id.strip()

    plan_id = payload.get("plan_id")
    if plan_id:
        return str(plan_id).strip()

    plan_file_path = payload.get("plan_file_path", "")
    extracted = extract_plan_id_from_path(plan_file_path)
    return extracted.strip() if extracted else None


async def _plan_ingress_impl(path_plan_id: str | None, payload: dict):
    """
    Accepts either:
      - /plans/ingress with JSON body: {"plan_id": "..."} or {"plan_file_path": "..."}
      - /plans/{plan_id}/ingress with optional JSON body
    """
    plan_id = _resolve_plan_id(path_plan_id, payload or {})
    if not plan_id:
        raise HTTPException(status_code=400, detail="Unable to determine plan_id; provide plan_id or plan_file_path")

    sm = PLAN_STATE_MACHINES.get(plan_id)
    if not sm:
<<<<<<< HEAD
        sm = StateMachine(max_retries=3)
=======
        sm = StateMachine(max_retries=3, persistence_callback=persistence_callback)
>>>>>>> cde431b91765a0efa58a544c6bbce7e87c940fbe
        sm.plan_id = plan_id

        # restored machines still need the EXECUTING callback to launch processing
        _register_executing_callback(sm, sm)
        PLAN_STATE_MACHINES[plan_id] = sm

    rec = sm.trigger("OBJECTIVE_INGRESS")
    return {"status": "scheduled", "plan_id": plan_id, "transition": rec.to_dict()}


@app.post("/plans/ingress")
async def plan_ingress(payload: dict = Body(...)):
    return await _plan_ingress_impl(None, payload)


@app.post("/plans/{plan_id}/ingress")
async def plan_ingress_by_id(plan_id: str, payload: dict = Body(default={})):
    return await _plan_ingress_impl(plan_id, payload)
<<<<<<< HEAD
=======


@app.post("/orchestrate")
async def orchestrate(user_query: str):
    """
    Triggers the full A2A pipeline (Managing->Orchestration->Architecture->Coder->Tester).
    Matches the contract expected by mcp_server.py.
    """
    engine = IntentEngine()
    # Run the pipeline in background or wait?
    # For MVP synchronous wait is acceptable, though blocking.
    # The mcp_server.py expects a response.
    
    try:
        result = await engine.run_full_pipeline(description=user_query, requester="api_user")
        
        # Summarize results
        summary = {
            "status": "A2A Workflow Complete",
            "success": result.success,
            "pipeline_results": {
                "plan_id": result.plan.plan_id,
                "blueprint_id": result.blueprint.plan_id,
                "code_artifacts": [a.artifact_id for a in result.code_artifacts],
            },
            # Return last code artifact content as 'final_code' for the MCP tool
            "final_code": result.code_artifacts[-1].content if result.code_artifacts else None,
            "test_summary": f"Passed: {sum(1 for v in result.test_verdicts if v['status'] == 'PASS')}/{len(result.test_verdicts)}"
        }
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
>>>>>>> cde431b91765a0efa58a544c6bbce7e87c940fbe
