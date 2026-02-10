# inside A2A_MCP/orchestrator/webhook.py
from fastapi import FastAPI, HTTPException, Body
from orchestrator.stateflow import StateMachine
from orchestrator.utils import extract_plan_id_from_path

app = FastAPI(...)

# in-memory map (replace with DB-backed persistence or plan state store in prod)
PLAN_STATE_MACHINES = {}

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
        # create the state machine; you might pass persistence hook here
        from orchestrator.stateflow import StateMachine
        sm = StateMachine(max_retries=3)
        sm.plan_id = plan_id
        PLAN_STATE_MACHINES[plan_id] = sm

    rec = sm.trigger("OBJECTIVE_INGRESS")
    return {"status": "scheduled", "plan_id": plan_id, "transition": rec.to_dict()}
