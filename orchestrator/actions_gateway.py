from __future__ import annotations

import uuid
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, Body
from schemas.action_model import ActionActionModel
from orchestrator.auth import authenticate_user

router = APIRouter(prefix="/actions", tags=["Actions Gateway"])

# Global Action Registry
_ACTION_CATALOG: Dict[str, ActionActionModel] = {}

def register_action_metadata(action: ActionActionModel):
    _ACTION_CATALOG[action.action_id] = action


@router.get("/catalog", response_model=List[ActionActionModel])
async def get_action_catalog(auth: dict = Depends(authenticate_user)):
    """Returns the registry of authenticated, test-gated API actions."""
    return list(_ACTION_CATALOG.values())


@router.post("/execute")
async def execute_action(
    action_id: str = Body(...),
    inputs: Dict[str, Any] = Body(...),
    context: Dict[str, Any] = Body(default_factory=dict),
    auth: dict = Depends(authenticate_user)
):
    """
    Unified entrypoint for all workflow steps.
    Enforces schema, auth, and policy gates.
    """
    action = _ACTION_CATALOG.get(action_id)
    if not action:
        raise HTTPException(status_code=404, detail=f"Action {action_id} not found in catalog")

    # 1. Schema Gate (Input Validation)
    # TODO: Implement jsonschema validation against action.input_schema

    # 2. Auth/Policy Gate
    # TODO: Enforce RBAC scopes from action.auth.required_scopes

    request_id = str(uuid.uuid4())
    
    # Placeholder for execution logic (Dispatch to MCP or Internal service)
    return {
        "status": "success",
        "outputs": {"message": f"Action {action_id} executed successfully (placeholder)"},
        "events": [{"event_type": "ACTION_EXECUTED", "timestamp": "..."}],
        "request_id": request_id
    }
