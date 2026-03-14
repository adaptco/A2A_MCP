import os
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, Optional

from fastapi import BackgroundTasks, Body, FastAPI, Header, HTTPException

from orchestrator import storage
from orchestrator.stateflow import StateMachine
from orchestrator.utils import extract_plan_id_from_path

if TYPE_CHECKING:
    from orchestrator.intent_engine import IntentEngine

app = FastAPI(title="A2A MCP Orchestrator")

# In-memory cache of live state machines.
PLAN_STATE_MACHINES: dict[str, StateMachine] = {}
RELEASE_JOBS: Dict[str, Dict[str, Any]] = {}
WEBHOOK_SHARED_SECRET = os.getenv("WEBHOOK_SHARED_SECRET", "")
_engine: Optional["IntentEngine"] = None


def _get_engine() -> "IntentEngine":
    global _engine
    if _engine is None:
        from orchestrator.intent_engine import IntentEngine
        _engine = IntentEngine()
    return _engine


def _validate_webhook_secret(token: Optional[str]) -> None:
    # Secret is optional for local/dev usage; enforce it when configured.
    if WEBHOOK_SHARED_SECRET and token != WEBHOOK_SHARED_SECRET:
        raise HTTPException(status_code=401, detail="invalid webhook token")


def _persistence_callback(plan_id: str | None, snapshot: dict) -> None:
    if not plan_id:
        return
    storage.save_plan_state(plan_id, snapshot)


def _load_or_create_machine(plan_id: str) -> StateMachine:
    sm = PLAN_STATE_MACHINES.get(plan_id)
    if sm:
        return sm

    persisted_snapshot = storage.load_plan_state(plan_id)
    if persisted_snapshot:
        sm = StateMachine.from_dict(
            persisted_snapshot,
            persistence_callback=lambda pid, snap: _persistence_callback(pid, snap),
        )
    else:
        sm = StateMachine(
            max_retries=3,
            persistence_callback=lambda pid, snap: _persistence_callback(pid, snap),
        )

    sm.plan_id = plan_id
    PLAN_STATE_MACHINES[plan_id] = sm
    return sm


@app.post("/plans/ingress")
async def plan_ingress(payload: dict = Body(...)):
    """
    Accept either:
    - plan_id: canonical id
    - plan_file_path: path containing the plan id in basename
    """
    plan_id = payload.get("plan_id")
    if not plan_id:
        plan_file_path = payload.get("plan_file_path", "")
        plan_id = extract_plan_id_from_path(plan_file_path)

    if not plan_id:
        raise HTTPException(
            status_code=400,
            detail="Unable to determine plan_id; provide plan_id or plan_file_path",
        )

    plan_id = plan_id.strip()
    sm = _load_or_create_machine(plan_id)

    try:
        rec = sm.trigger("OBJECTIVE_INGRESS")
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return {"status": "scheduled", "plan_id": plan_id, "transition": rec.to_dict()}


@app.post("/plans/{plan_id}/ingress")
async def plan_ingress_by_id(plan_id: str):
    plan_id = plan_id.strip()
    if not plan_id:
        raise HTTPException(status_code=400, detail="plan_id is required")

    sm = _load_or_create_machine(plan_id)

    try:
        rec = sm.trigger("OBJECTIVE_INGRESS")
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return {"status": "scheduled", "plan_id": plan_id, "transition": rec.to_dict()}


@app.post("/plans/{plan_id}/dispatch")
async def dispatch_plan(plan_id: str):
    plan_id = plan_id.strip()
    if not plan_id:
        raise HTTPException(status_code=400, detail="plan_id is required")

    sm = _load_or_create_machine(plan_id)

    try:
        rec = sm.trigger("RUN_DISPATCHED")
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return {"status": "ok", "plan_id": plan_id, "transition": rec.to_dict()}


@app.get("/plans/{plan_id}/state")
async def get_plan_state(plan_id: str):
    plan_id = plan_id.strip()
    if not plan_id:
        raise HTTPException(status_code=400, detail="plan_id is required")

    sm = PLAN_STATE_MACHINES.get(plan_id)
    if sm:
        return {"plan_id": plan_id, "snapshot": sm.to_dict()}

    persisted_snapshot = storage.load_plan_state(plan_id)
    if not persisted_snapshot:
        raise HTTPException(status_code=404, detail="no plan")

    return {"plan_id": plan_id, "snapshot": persisted_snapshot}


@app.post("/webhooks/release")
async def release_webhook(
    payload: dict = Body(...),
    background: BackgroundTasks = None,
    x_webhook_token: Optional[str] = Header(default=None, alias="X-Webhook-Token"),
    x_webhook_provider: Optional[str] = Header(default="generic", alias="X-Webhook-Provider"),
    x_webhook_event: Optional[str] = Header(default="release", alias="X-Webhook-Event"),
):
    _validate_webhook_secret(x_webhook_token)

    release_id = str(uuid.uuid4())
    RELEASE_JOBS[release_id] = {
        "release_id": release_id,
        "status": "accepted",
        "provider": x_webhook_provider or "generic",
        "event_type": x_webhook_event or "release",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "result": None,
        "error": None,
    }

    async def _run_job() -> None:
        RELEASE_JOBS[release_id]["status"] = "running"
        RELEASE_JOBS[release_id]["started_at"] = datetime.now(timezone.utc).isoformat()
        try:
            result = await _get_engine().run_release_workflow_from_webhook(
                payload=payload,
                provider=x_webhook_provider or "generic",
                event_type=x_webhook_event or "release",
            )
            RELEASE_JOBS[release_id]["status"] = "completed"
            RELEASE_JOBS[release_id]["result"] = result
            RELEASE_JOBS[release_id]["completed_at"] = datetime.now(timezone.utc).isoformat()
        except Exception as exc:
            RELEASE_JOBS[release_id]["status"] = "failed"
            RELEASE_JOBS[release_id]["error"] = str(exc)
            RELEASE_JOBS[release_id]["completed_at"] = datetime.now(timezone.utc).isoformat()

    if background is None:
        # Log a warning or raise an error if background tasks are expected but not provided
        # For now, we'll just run it directly, but this might block the request.
        self.logger.warning("BackgroundTasks not provided, running release job synchronously.")
        await _run_job()
    else:
        background.add_task(_run_job)

    return {"status": "accepted", "release_id": release_id}


@app.get("/webhooks/release/{release_id}")
async def get_release_status(release_id: str):
    job = RELEASE_JOBS.get(release_id)
    if not job:
        raise HTTPException(status_code=404, detail="release job not found")
    return job
