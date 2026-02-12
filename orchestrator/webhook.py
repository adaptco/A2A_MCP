# inside A2A_MCP/orchestrator/webhook.py
from fastapi import FastAPI, HTTPException, Body
from orchestrator.stateflow import StateMachine
from orchestrator.utils import extract_plan_id_from_path
from orchestrator.storage import save_plan_state
from orchestrator.intent_engine import IntentEngine
import asyncio

app = FastAPI(title="A2A Plan Orchestrator")

# in-memory map (replace with DB-backed persistence or plan state store in prod)
PLAN_STATE_MACHINES = {}

def persistence_callback(plan_id: str, state_dict: dict) -> None:
    """Callback to persist FSM state to database."""
    try:
        save_plan_state(plan_id, state_dict)
    except Exception as e:
        print(f"Warning: Failed to persist plan state for {plan_id}: {e}")

@app.post("/plans/ingress")
async def plan_ingress(payload: dict = Body(...)):
    """
    Accepts:
      - plan_id: optional canonical id
      - plan_file_path: optional file path that contains plan id in its basename
    Prioritizes plan_id if given; otherwise tries to extract id from plan_file_path.
    """
    plan_id = payload.get("plan_id")
    if not plan_id:
        plan_file_path = payload.get("plan_file_path", "")
        plan_id = extract_plan_id_from_path(plan_file_path)
    if not plan_id:
        raise HTTPException(status_code=400, detail="Unable to determine plan_id; provide plan_id or plan_file_path")
    # Ensure plan_id is sanitized
    plan_id = plan_id.strip()
    # Create or reuse an FSM for plan
    sm = PLAN_STATE_MACHINES.get(plan_id)
    if not sm:
        # Create the state machine with persistence callback
        sm = StateMachine(max_retries=3, persistence_callback=persistence_callback)
        sm.plan_id = plan_id
        PLAN_STATE_MACHINES[plan_id] = sm

    rec = sm.trigger("OBJECTIVE_INGRESS")
    return {"status": "scheduled", "plan_id": plan_id, "transition": rec.to_dict()}


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
