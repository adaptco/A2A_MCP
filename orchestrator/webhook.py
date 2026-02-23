from __future__ import annotations

import uuid
from typing import Optional

from fastapi import Body, FastAPI, Header, HTTPException

from orchestrator.intent_engine import IntentEngine
from orchestrator.runtime_bridge import (
    HandshakeInitRequest,
    build_handshake_bundle,
    fingerprint_secret,
)
from orchestrator.stateflow import StateMachine
from orchestrator.storage import DBManager, save_plan_state
from orchestrator.utils import extract_plan_id_from_path

app = FastAPI(title="A2A MCP Webhook")

# in-memory map (replace with DB-backed persistence or plan state store in prod)
PLAN_STATE_MACHINES = {}


def persistence_callback(plan_id: str, state_dict: dict) -> None:
    """Callback to persist FSM state to database."""
    try:
        save_plan_state(plan_id, state_dict)
    except Exception as exc:  # pragma: no cover - best effort persistence
        print(f"Warning: Failed to persist plan state for {plan_id}: {exc}")


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
        raise HTTPException(
            status_code=400,
            detail="Unable to determine plan_id; provide plan_id or plan_file_path",
        )

    sm = PLAN_STATE_MACHINES.get(plan_id)
    if not sm:
        sm = StateMachine(max_retries=3, persistence_callback=persistence_callback)
        sm.plan_id = plan_id
        PLAN_STATE_MACHINES[plan_id] = sm

    rec = sm.trigger("OBJECTIVE_INGRESS")
    return {"status": "scheduled", "plan_id": plan_id, "transition": rec.to_dict()}


@app.post("/plans/ingress")
async def plan_ingress(payload: dict = Body(...)):
    return await _plan_ingress_impl(None, payload)


@app.post("/plans/{plan_id}/ingress")
async def plan_ingress_by_id(plan_id: str, payload: dict = Body(default={})):
    return await _plan_ingress_impl(plan_id, payload)


@app.post("/handshake/init")
async def initialize_handshake(
    payload: HandshakeInitRequest = Body(...),
    x_api_key: Optional[str] = Header(default=None),
):
    """
    Initialize MCP handshake with full state payload and runtime assignment
    bridge artifact generation.
    """
    api_key = (x_api_key or payload.mcp.api_key or "").strip()
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="API key required for MCP handshake initialization",
        )

    api_key_fingerprint = fingerprint_secret(api_key)
    plan_id = (payload.plan_id or "").strip() or f"plan-{uuid.uuid4().hex[:10]}"
    handshake_id = f"hs-{uuid.uuid4().hex[:12]}"

    sm = PLAN_STATE_MACHINES.get(plan_id)
    if not sm:
        sm = StateMachine(max_retries=3, persistence_callback=persistence_callback)
        sm.plan_id = plan_id
        PLAN_STATE_MACHINES[plan_id] = sm

    transition = None
    if sm.current_state().value == "IDLE":
        transition = sm.trigger(
            "OBJECTIVE_INGRESS",
            actor=payload.actor,
            handshake_id=handshake_id,
        ).to_dict()

    handshake_bundle = build_handshake_bundle(
        db_manager=DBManager(),
        payload=payload,
        plan_id=plan_id,
        handshake_id=handshake_id,
        api_key_fingerprint=api_key_fingerprint,
    )
    state_payload = {
        "handshake_id": handshake_id,
        "plan_id": plan_id,
        "state_machine": sm.to_dict(),
        "transition": transition,
        **handshake_bundle,
    }

    return {
        "status": "handshake_initialized",
        "message": "Agents onboarded as stateful embedding artifacts.",
        "state_payload": state_payload,
    }


@app.post("/orchestrate")
async def orchestrate(user_query: str):
    """
    Triggers the full A2A pipeline (Managing->Orchestration->Architecture->Coder->Tester).
    Matches the contract expected by mcp_server.py.
    """
    engine = IntentEngine()

    try:
        result = await engine.run_full_pipeline(
            description=user_query,
            requester="api_user",
        )

        return {
            "status": "A2A Workflow Complete",
            "success": result.success,
            "pipeline_results": {
                "plan_id": result.plan.plan_id,
                "blueprint_id": result.blueprint.plan_id,
                "code_artifacts": [a.artifact_id for a in result.code_artifacts],
            },
            "final_code": result.code_artifacts[-1].content if result.code_artifacts else None,
            "test_summary": (
                f"Passed: {sum(1 for v in result.test_verdicts if v['status'] == 'PASS')}"
                f"/{len(result.test_verdicts)}"
            ),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
