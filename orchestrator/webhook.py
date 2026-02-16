from fastapi import FastAPI, HTTPException, Body
from orchestrator.stateflow import StateMachine
from orchestrator.utils import extract_plan_id_from_path

app = FastAPI(title="A2A MCP Webhook")

# in-memory map (replace with DB-backed persistence or plan state store in prod)
PLAN_STATE_MACHINES = {}


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
        sm = StateMachine(max_retries=3)
        sm.plan_id = plan_id

        # restored machines still need the EXECUTING callback to launch processing
        def on_executing(rec):
            async def run_engine():
                try:
                    await engine.process_plan(plan)
                    sm.trigger("EXECUTION_COMPLETE", artifact_id="...")
                except Exception as exc:
                    sm.trigger("EXECUTION_ERROR", details=str(exc))
            import asyncio
            asyncio.create_task(run_engine())

        sm.register_callback(State.EXECUTING, on_executing)
        PLAN_STATE_MACHINES[plan_id] = sm

    rec = sm.trigger("OBJECTIVE_INGRESS")
    return {"status": "scheduled", "plan_id": plan_id, "transition": rec.to_dict()}


@app.post("/plans/ingress")
async def plan_ingress(payload: dict = Body(...)):
    return await _plan_ingress_impl(None, payload)


@app.post("/plans/{plan_id}/ingress")
async def plan_ingress_by_id(plan_id: str, payload: dict = Body(default={})):
    return await _plan_ingress_impl(plan_id, payload)
