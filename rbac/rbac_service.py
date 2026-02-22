"""
RBAC Gateway — FastAPI microservice for agent onboarding and permission checks.

Provides role-based access control for agents entering the embedding vector
pipeline and executing lifecycle transitions.
"""

from __future__ import annotations

import os
from typing import Dict

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from rbac.models import (
    ACTION_PERMISSIONS,
    ROLE_PERMISSIONS,
    AgentRecord,
    AgentRegistration,
    AgentRole,
    OnboardingResult,
    PermissionCheckRequest,
    PermissionCheckResponse,
)

# ── App setup ────────────────────────────────────────────────────────────

app = FastAPI(
    title="A2A RBAC Gateway",
    description="Agent onboarding and permission enforcement for the A2A MCP pipeline.",
    version="1.0.0",
)

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory agent registry (MVP — swap for DB-backed store in production)
_registry: Dict[str, AgentRecord] = {}

RBAC_SECRET = os.getenv("RBAC_SECRET", "dev-secret-change-me")


# ── Health ───────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "rbac-gateway",
        "registered_agents": len(_registry),
    }


# ── Agent Onboarding ────────────────────────────────────────────────────

@app.post("/agents/onboard", response_model=OnboardingResult, status_code=201)
async def onboard_agent(registration: AgentRegistration):
    """
    Register a new agent with a role and optional embedding config.

    The agent's role determines which lifecycle transitions and actions it
    may perform within the pipeline.
    """
    if registration.agent_id in _registry:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Agent '{registration.agent_id}' is already registered.",
        )

    record = AgentRecord(
        agent_id=registration.agent_id,
        agent_name=registration.agent_name,
        role=registration.role,
        embedding_config=registration.embedding_config,
        metadata=registration.metadata,
    )
    _registry[registration.agent_id] = record

    # Build permission lists from role
    transitions = sorted(ROLE_PERMISSIONS.get(record.role, set()))
    actions = sorted(ACTION_PERMISSIONS.get(record.role, set()))

    return OnboardingResult(
        agent_id=record.agent_id,
        agent_name=record.agent_name,
        role=record.role,
        permissions=transitions,
        actions=actions,
    )


# ── Permission Queries ──────────────────────────────────────────────────

@app.get("/agents/{agent_id}/permissions")
async def get_agent_permissions(agent_id: str):
    """Return the full permission scope for a registered agent."""
    record = _registry.get(agent_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found.",
        )

    return {
        "agent_id": record.agent_id,
        "agent_name": record.agent_name,
        "role": record.role.value,
        "transitions": sorted(ROLE_PERMISSIONS.get(record.role, set())),
        "actions": sorted(ACTION_PERMISSIONS.get(record.role, set())),
        "active": record.active,
    }


@app.post("/agents/{agent_id}/verify", response_model=PermissionCheckResponse)
async def verify_permission(agent_id: str, check: PermissionCheckRequest):
    """
    Check whether an agent is permitted to perform a specific action or
    lifecycle transition.
    """
    record = _registry.get(agent_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found.",
        )

    if not record.active:
        return PermissionCheckResponse(
            agent_id=agent_id,
            allowed=False,
            role=record.role,
            reason="Agent is deactivated.",
        )

    # Check action permission
    if check.action:
        allowed_actions = ACTION_PERMISSIONS.get(record.role, set())
        if check.action in allowed_actions:
            return PermissionCheckResponse(
                agent_id=agent_id,
                allowed=True,
                role=record.role,
                reason=f"Action '{check.action}' permitted for role '{record.role.value}'.",
            )
        return PermissionCheckResponse(
            agent_id=agent_id,
            allowed=False,
            role=record.role,
            reason=f"Action '{check.action}' not permitted for role '{record.role.value}'.",
        )

    # Check lifecycle transition permission
    if check.transition:
        allowed_transitions = ROLE_PERMISSIONS.get(record.role, set())
        if check.transition in allowed_transitions:
            return PermissionCheckResponse(
                agent_id=agent_id,
                allowed=True,
                role=record.role,
                reason=f"Transition '{check.transition}' permitted for role '{record.role.value}'.",
            )
        return PermissionCheckResponse(
            agent_id=agent_id,
            allowed=False,
            role=record.role,
            reason=f"Transition '{check.transition}' not permitted for role '{record.role.value}'.",
        )

    return PermissionCheckResponse(
        agent_id=agent_id,
        allowed=False,
        role=record.role,
        reason="No action or transition specified in the check request.",
    )


# ── Agent Management ────────────────────────────────────────────────────

@app.get("/agents")
async def list_agents():
    """List all registered agents."""
    return {
        "agents": [
            {
                "agent_id": r.agent_id,
                "agent_name": r.agent_name,
                "role": r.role.value,
                "active": r.active,
            }
            for r in _registry.values()
        ]
    }


@app.delete("/agents/{agent_id}", status_code=204)
async def deactivate_agent(agent_id: str):
    """Soft-deactivate an agent (preserves record for audit)."""
    record = _registry.get(agent_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found.",
        )
    record.active = False


# ── Entry point ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
