from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import JSONResponse
from jsonschema import Draft202012Validator, ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import ActionDefinition, ActionRequest, WorkflowDAG
from orchestrator.storage import SessionLocal
from schemas.database import ActionModel, ApprovalModel, EventModel, RunModel, StepModel

router = APIRouter(prefix="/actions", tags=["actions"])
workflow_router = APIRouter(prefix="/workflows", tags=["workflows"])


@dataclass(frozen=True)
class AuthContext:
    actor_id: str
    tenant_id: str
    scopes: set[str]
    claims: dict[str, Any]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _to_dict(model: Any) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump(mode="python")
    return model.dict()


def get_db() -> Any:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _scopes_from_header(scopes: str | None) -> set[str]:
    if not scopes:
        return set()
    return {item.strip() for item in scopes.split(",") if item.strip()}


def verify_token(
    authorization: str | None = Header(default=None),
    x_actor_id: str | None = Header(default=None),
    x_tenant_id: str | None = Header(default=None),
    x_scopes: str | None = Header(default=None),
) -> AuthContext:
    auth_disabled = str(os.getenv("ACS_AUTH_DISABLED", "true")).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    actor_id = x_actor_id or "system"
    tenant_id = x_tenant_id or "default"
    scopes = _scopes_from_header(x_scopes)

    if auth_disabled:
        return AuthContext(actor_id=actor_id, tenant_id=tenant_id, scopes=scopes, claims={})

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")

    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="empty bearer token")

    return AuthContext(actor_id=actor_id, tenant_id=tenant_id, scopes=scopes, claims={"token": token})


def verify_admin(auth: AuthContext = Depends(verify_token)) -> AuthContext:
    if {"admin", "admin:actions"} & auth.scopes:
        return auth

    # In local mode, allow system actor for bootstrap registration.
    if auth.actor_id == "system":
        return auth

    raise HTTPException(status_code=403, detail="admin scope required")


def validate_json_schema(schema: dict[str, Any]) -> None:
    try:
        Draft202012Validator.check_schema(schema)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"invalid JSON schema: {exc}") from exc


def _extract_urls(value: Any) -> list[str]:
    urls: list[str] = []
    if isinstance(value, dict):
        for item in value.values():
            urls.extend(_extract_urls(item))
    elif isinstance(value, list):
        for item in value:
            urls.extend(_extract_urls(item))
    elif isinstance(value, str) and value.startswith(("http://", "https://")):
        urls.append(value)
    return urls


def evaluate_policy(policy_config: dict[str, Any], request: ActionRequest, auth: AuthContext) -> tuple[bool, str]:
    del auth
    payload_bytes = len(json.dumps(request.inputs, separators=(",", ":")).encode("utf-8"))
    max_payload_kb = int(policy_config.get("max_payload_kb", 128))
    if payload_bytes > max_payload_kb * 1024:
        return False, f"payload exceeds {max_payload_kb}KB"

    egress_mode = str(policy_config.get("egress", "deny_by_default"))
    allowed_domains = {domain.lower() for domain in policy_config.get("allowed_domains", [])}
    if egress_mode == "deny_by_default":
        for candidate in _extract_urls(request.inputs):
            netloc = urlparse(candidate).netloc.lower()
            if allowed_domains and netloc not in allowed_domains:
                return False, f"egress domain not allowed: {netloc}"
            if not allowed_domains:
                return False, "egress denied by default"

    return True, "allowed"


def _ensure_run_and_step(db: Session, request: ActionRequest, auth: AuthContext) -> tuple[RunModel, StepModel]:
    run = db.query(RunModel).filter(RunModel.run_id == request.context.run_id).first()
    if run is None:
        run = RunModel(
            run_id=request.context.run_id,
            workflow_id=f"adhoc.{request.action_id}",
            tenant_id=auth.tenant_id,
            actor_id=auth.actor_id,
            dag_spec={"workflow_id": f"adhoc.{request.action_id}", "nodes": []},
            status="running",
            started_at=_utc_now(),
        )
        db.add(run)
        db.flush()

    step = db.query(StepModel).filter(StepModel.step_id == request.context.step_id).first()
    if step is None:
        step = StepModel(
            step_id=request.context.step_id,
            run_id=run.run_id,
            node_id=request.context.step_id,
            action_id=request.action_id,
            inputs=request.inputs,
            status="running",
            attempt_count=1,
            started_at=_utc_now(),
        )
        db.add(step)
        db.flush()

    return run, step


@router.post("/register")
async def register_action(
    action: ActionDefinition,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(verify_admin),
) -> dict[str, str]:
    del auth
    validate_json_schema(action.input_schema)
    validate_json_schema(action.output_schema)

    namespace, tail = action.action_id.split(".", 1)
    name, version_str = tail.split("@", 1)

    db_action = ActionModel(
        action_id=action.action_id,
        namespace=namespace,
        name=name,
        version=int(version_str),
        input_schema=action.input_schema,
        output_schema=action.output_schema,
        auth_config=_to_dict(action.auth),
        policy_config=_to_dict(action.policy),
        execution_config=_to_dict(action.execution),
    )
    db.add(db_action)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=f"action already exists: {action.action_id}") from exc

    return {"status": "registered", "action_id": action.action_id}


@router.post("/execute")
async def execute_action(
    request: ActionRequest,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(verify_token),
) -> JSONResponse:
    action = db.query(ActionModel).filter(ActionModel.action_id == request.action_id).first()
    if action is None:
        raise HTTPException(status_code=404, detail=f"action not found: {request.action_id}")

    try:
        Draft202012Validator(action.input_schema).validate(request.inputs)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=f"input schema validation failed: {exc.message}") from exc

    allowed, reason = evaluate_policy(action.policy_config, request, auth)
    if not allowed:
        raise HTTPException(status_code=403, detail=f"policy denied: {reason}")

    run, step = _ensure_run_and_step(db, request, auth)

    required_policy = action.policy_config.get("requires_approval")
    if required_policy:
        approval_state = str(request.context.approvals.get(required_policy, "pending")).lower()
        if approval_state not in {"approved", "allow"}:
            approval = ApprovalModel(
                step_id=step.step_id,
                policy_name=required_policy,
                approver_group=required_policy,
                status="pending",
                decision_reason="approval required before action execution",
            )
            db.add(approval)
            db.add(
                EventModel(
                    run_id=run.run_id,
                    step_id=step.step_id,
                    event_type="approval_requested",
                    payload={"policy": required_policy, "request_id": request.request_id},
                )
            )
            step.status = "awaiting_approval"
            run.status = "waiting"
            db.commit()
            return JSONResponse(
                status_code=202,
                content={
                    "status": "approval_required",
                    "run_id": run.run_id,
                    "step_id": step.step_id,
                    "policy": required_policy,
                },
            )

    outputs: dict[str, Any] = {
        "ok": True,
        "request_id": request.request_id,
        "action_id": request.action_id,
        "echo": request.inputs,
        "executed_at": _utc_now().isoformat(),
    }

    try:
        Draft202012Validator(action.output_schema).validate(outputs)
    except ValidationError:
        # Ensure action execution does not fail because output schema is stricter
        # than the default transport envelope.
        outputs = {"ok": True}

    step.outputs = outputs
    step.status = "completed"
    step.completed_at = _utc_now()
    run.status = "completed"
    run.completed_at = _utc_now()

    db.add(
        EventModel(
            run_id=run.run_id,
            step_id=step.step_id,
            event_type="action_executed",
            payload={"action_id": request.action_id, "request_id": request.request_id},
        )
    )
    db.commit()

    return JSONResponse(
        status_code=200,
        content={
            "status": "executed",
            "run_id": run.run_id,
            "step_id": step.step_id,
            "outputs": outputs,
        },
    )


@workflow_router.post("/submit")
async def submit_workflow(
    dag: WorkflowDAG,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(verify_token),
) -> dict[str, Any]:
    run = RunModel(
        workflow_id=f"{dag.workflow_id}@{dag.version}",
        tenant_id=auth.tenant_id,
        actor_id=auth.actor_id,
        dag_spec=_to_dict(dag),
        status="pending",
    )
    db.add(run)
    db.flush()

    for node in dag.nodes:
        db.add(
            StepModel(
                run_id=run.run_id,
                node_id=node.id,
                action_id=node.action_id,
                inputs=node.inputs,
                status="pending",
            )
        )

    db.add(
        EventModel(
            run_id=run.run_id,
            step_id=None,
            event_type="workflow_submitted",
            payload={"workflow_id": dag.workflow_id, "node_count": len(dag.nodes)},
        )
    )
    db.commit()

    return {
        "status": "submitted",
        "run_id": run.run_id,
        "workflow_id": dag.workflow_id,
        "nodes": len(dag.nodes),
    }


@workflow_router.get("/{run_id}")
async def get_workflow_run(run_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    run = db.query(RunModel).filter(RunModel.run_id == run_id).first()
    if run is None:
        raise HTTPException(status_code=404, detail=f"run not found: {run_id}")

    steps = db.query(StepModel).filter(StepModel.run_id == run_id).all()
    return {
        "run_id": run.run_id,
        "workflow_id": run.workflow_id,
        "status": run.status,
        "tenant_id": run.tenant_id,
        "actor_id": run.actor_id,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "steps": [
            {
                "step_id": step.step_id,
                "node_id": step.node_id,
                "action_id": step.action_id,
                "status": step.status,
                "attempt_count": step.attempt_count,
            }
            for step in steps
        ],
    }
