from __future__ import annotations

import uuid
from typing import Optional, Dict

from fastapi import Body, FastAPI, Header, HTTPException
from fastapi.concurrency import run_in_threadpool

from orchestrator.intent_engine import IntentEngine
from orchestrator.runtime_bridge import (
    HandshakeInitRequest,
    build_handshake_bundle,
    fingerprint_secret,
)
from orchestrator.stateflow import StateMachine, State
from orchestrator.storage import DBManager, save_plan_state
from orchestrator.utils import extract_plan_id_from_path
from orchestrator.hmlsl_ledger import HMLSLLedgerManager

app = FastAPI(title="A2A MCP Webhook")

# in-memory map (TODO: replace with DB-backed persistence in prod)
PLAN_STATE_MACHINES = {}
PLAN_LEDGERS: Dict[str, HMLSLLedgerManager] = {}


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


def _get_or_create_plan_resources(
    plan_id: str
) -> tuple[StateMachine, HMLSLLedgerManager]:
    sm = PLAN_STATE_MACHINES.get(plan_id)
    ledger = PLAN_LEDGERS.get(plan_id)

    if not sm:
        sm = StateMachine(
            max_retries=3, persistence_callback=persistence_callback
        )
        sm.plan_id = plan_id
        PLAN_STATE_MACHINES[plan_id] = sm

    if not ledger:
        ledger = HMLSLLedgerManager(plan_id)
        PLAN_LEDGERS[plan_id] = ledger

        # Register callback to log transitions to ledger
        def log_transition(record):
            ledger.add_behavioral_trace(
                step_description=f"Transition to {record.to_state.value}",
                tool_invocation={
                    "tool_name": "stateflow", "event": record.event
                },
                result=str(record.meta)
            )

        for state in State:
            sm.register_callback(state, log_transition)

    return sm, ledger


async def _plan_ingress_impl(path_plan_id: str | None, payload: dict):
    """
    Accepts either:
      - /plans/ingress with JSON body: {"plan_id": "..."} or ...
      - /plans/{plan_id}/ingress with optional JSON body
    """
    plan_id = _resolve_plan_id(path_plan_id, payload or {})
    if not plan_id:
        raise HTTPException(
            status_code=400,
            detail="Unable to determine plan_id; provide plan_id or path",
        )

    sm, ledger = _get_or_create_plan_resources(plan_id)

    rec = await run_in_threadpool(sm.trigger, "OBJECTIVE_INGRESS")
    return {
        "status": "scheduled",
        "plan_id": plan_id,
        "transition": rec.to_dict(),
    }


@app.post("/plans/ingress")
async def plan_ingress(payload: dict = Body(...)):
    return await _plan_ingress_impl(None, payload)


@app.post("/plans/{plan_id}/ingress")
async def plan_ingress_by_id(plan_id: str, payload: dict = Body(default={})):
    return await _plan_ingress_impl(plan_id, payload)


@app.get("/plans/{plan_id}/ledger")
async def get_plan_ledger(plan_id: str):
    """
    Retrieve the Hierarchical Multi-Layered Semantic Ledger (HMLSL) artifact.
    """
    ledger = PLAN_LEDGERS.get(plan_id)
    if not ledger:
        # Try to recreate if SM exists, or fail
        if plan_id in PLAN_STATE_MACHINES:
            _, ledger = _get_or_create_plan_resources(plan_id)
        else:
            raise HTTPException(status_code=404, detail="Plan not found")

    # Finalize generates the artifact with clustering, weights, and merkle root
    artifact = await run_in_threadpool(ledger.finalize)
    return artifact.model_dump(by_alias=True)


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
    plan_id = (payload.plan_id or "").strip()
    if not plan_id:
        plan_id = f"plan-{uuid.uuid4().hex[:10]}"
    handshake_id = f"hs-{uuid.uuid4().hex[:12]}"

    sm, ledger = _get_or_create_plan_resources(plan_id)

    transition = None
    if sm.current_state().value == "IDLE":
        rec = await run_in_threadpool(
            sm.trigger,
            "OBJECTIVE_INGRESS",
            actor=payload.actor,
            handshake_id=handshake_id,
        )
        transition = rec.to_dict()

    # Log Structural Node for the handshake
    ledger.add_structural_node(
        contract_type="MCP_HANDSHAKE",
        definition={
            "handshake_id": handshake_id,
            "mcp": payload.mcp.model_dump(),
            "runtime": payload.runtime.model_dump()
        }
    )

    handshake_bundle = await run_in_threadpool(
        build_handshake_bundle,
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
    Triggers the full A2A pipeline (Managing->...->Tester).
    Matches the contract expected by mcp_server.py.
    """
    engine = IntentEngine()

    try:
        result = await engine.run_full_pipeline(
            description=user_query,
            requester="api_user",
        )

        test_pass_count = sum(
            1 for v in result.test_verdicts if v['status'] == 'PASS'
        )
        total_tests = len(result.test_verdicts)

        # If we had access to plan_id here easily, we should log to ledger.
        # result.plan.plan_id is available.
        if result.plan and result.plan.plan_id:
            _, ledger = _get_or_create_plan_resources(result.plan.plan_id)
            ledger.add_behavioral_trace(
                step_description="Full Pipeline Execution Complete",
                tool_invocation={
                    "tool_name": "orchestrator", "query": user_query
                },
                result="Success" if result.success else "Fail"
            )

        return {
            "status": "A2A Workflow Complete",
            "success": result.success,
            "pipeline_results": {
                "plan_id": result.plan.plan_id,
                "blueprint_id": result.blueprint.plan_id,
                "code_artifacts": [
                    a.artifact_id for a in result.code_artifacts
                ],
            },
            "final_code": (
                result.code_artifacts[-1].content
                if result.code_artifacts else None
            ),
            "test_summary": f"Passed: {test_pass_count}/{total_tests}",
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
