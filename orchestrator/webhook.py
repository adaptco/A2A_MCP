from fastapi import FastAPI, HTTPException, BackgroundTasks
from orchestrator.stateflow import StateMachine, State
from orchestrator.intent_engine import IntentEngine
from orchestrator.scheduler import SimpleScheduler
from orchestrator import storage

app = FastAPI(...)
engine = IntentEngine()

# in-memory cache of live state machines
PLAN_STATE_MACHINES = {}
SCHED = SimpleScheduler()


def _register_executing_callback(sm: StateMachine, plan) -> None:
    """Register the EXECUTING callback that launches the intent engine."""

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

@app.post("/plans/{plan_id}/ingress")
async def plan_ingress(plan_id: str, background: BackgroundTasks):
    # Create or fetch persisted state machine snapshot
    persisted_snapshot = storage.load_plan_state(plan_id)
    if persisted_snapshot:
        sm = StateMachine.from_dict(
            persisted_snapshot,
            persistence_callback=lambda pid, snap: storage.save_plan_state(pid, snap),
        )
    else:
        sm = StateMachine(
            max_retries=3,
            persistence_callback=lambda pid, snap: storage.save_plan_state(pid, snap),
        )
    sm.plan_id = plan_id

    # register callback: when executing, run the intent engine
    _register_executing_callback(sm, sm)
    # persist mapping
    PLAN_STATE_MACHINES[plan_id] = sm
    rec = sm.trigger("OBJECTIVE_INGRESS")
    return {"status":"ok","transition":rec.__dict__}

@app.post("/plans/{plan_id}/dispatch")
async def dispatch_plan(plan_id: str):
    sm = PLAN_STATE_MACHINES.get(plan_id)
    if not sm:
        persisted_snapshot = storage.load_plan_state(plan_id)
        if not persisted_snapshot:
            raise HTTPException(404, "no plan")
        sm = StateMachine.from_dict(
            persisted_snapshot,
            persistence_callback=lambda pid, snap: storage.save_plan_state(pid, snap),
        )
        sm.plan_id = plan_id

        # restored machines still need the EXECUTING callback to launch processing
        _register_executing_callback(sm, sm)
        PLAN_STATE_MACHINES[plan_id] = sm
    rec = sm.trigger("RUN_DISPATCHED")
    return {"status":"ok","transition":rec.__dict__}
