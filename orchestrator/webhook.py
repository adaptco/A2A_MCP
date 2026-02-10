from fastapi import FastAPI, HTTPException, BackgroundTasks
from orchestrator.stateflow import StateMachine, State
from orchestrator.intent_engine import IntentEngine
from orchestrator.scheduler import SimpleScheduler

app = FastAPI(...)
engine = IntentEngine()

# in-memory plan store for demo (persist to DB in prod)
PLAN_STATE_MACHINES = {}
SCHED = SimpleScheduler()

@app.post("/plans/{plan_id}/ingress")
async def plan_ingress(plan_id: str, background: BackgroundTasks):
    # Create or fetch plan and create state machine
    sm = StateMachine(max_retries=3)
    # register callback: when executing, run the intent engine
    def on_executing(rec):
        # run IntentEngine asynchronously
        async def run_engine():
            try:
                await engine.process_plan(plan)  # plan must be loaded or passed in
                # after engine finishes: trigger completion
                sm.trigger("EXECUTION_COMPLETE", artifact_id="...") 
            except Exception as exc:
                # on error trigger repair
                sm.trigger("EXECUTION_ERROR", details=str(exc))
        import asyncio
        asyncio.create_task(run_engine())

    sm.register_callback(State.EXECUTING, on_executing)
    # persist mapping
    PLAN_STATE_MACHINES[plan_id] = sm
    rec = sm.trigger("OBJECTIVE_INGRESS")
    return {"status":"ok","transition":rec.__dict__}

@app.post("/plans/{plan_id}/dispatch")
async def dispatch_plan(plan_id: str):
    sm = PLAN_STATE_MACHINES.get(plan_id)
    if not sm:
        raise HTTPException(404, "no plan")
    rec = sm.trigger("RUN_DISPATCHED")
    return {"status":"ok","transition":rec.__dict__}
