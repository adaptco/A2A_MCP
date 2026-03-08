"""
RBAC Models — Pydantic schemas for agent onboarding and permission checks.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, Field


class AgentRole(str, Enum):
    """Roles that govern what lifecycle transitions an agent may perform."""

    ADMIN = "admin"                       # All transitions
    PIPELINE_OPERATOR = "pipeline_operator"  # Full INIT → CONVERGED flow
    HEALER = "healer"                     # HEALING ↔ LORA_ADAPT loop only
    OBSERVER = "observer"                 # Read-only, no transitions


# ── Permission matrix ────────────────────────────────────────────────────
# Maps each role to the set of lifecycle transitions it may trigger.
# Transition keys are "FROM→TO" strings matching AgentLifecycleState values.

ROLE_PERMISSIONS: Dict[AgentRole, Set[str]] = {
    AgentRole.ADMIN: {
        "INIT→EMBEDDING",
        "EMBEDDING→RAG_QUERY",
        "EMBEDDING→FAILED",
        "RAG_QUERY→LORA_ADAPT",
        "RAG_QUERY→FAILED",
        "LORA_ADAPT→HEALING",
        "LORA_ADAPT→FAILED",
        "HEALING→CONVERGED",
        "HEALING→LORA_ADAPT",
        "HEALING→FAILED",
        "FAILED→INIT",
    },
    AgentRole.PIPELINE_OPERATOR: {
        "INIT→EMBEDDING",
        "EMBEDDING→RAG_QUERY",
        "RAG_QUERY→LORA_ADAPT",
        "LORA_ADAPT→HEALING",
        "HEALING→CONVERGED",
        "HEALING→LORA_ADAPT",
    },
    AgentRole.HEALER: {
        "HEALING→LORA_ADAPT",
        "LORA_ADAPT→HEALING",
        "HEALING→CONVERGED",
    },
    AgentRole.OBSERVER: set(),
}

# ── Additional action permissions ────────────────────────────────────────

ACTION_PERMISSIONS: Dict[AgentRole, Set[str]] = {
    AgentRole.ADMIN: {"run_pipeline", "onboard_agent", "view_artifacts", "manage_roles"},
    AgentRole.PIPELINE_OPERATOR: {"run_pipeline", "view_artifacts"},
    AgentRole.HEALER: {"run_healing", "view_artifacts"},
    AgentRole.OBSERVER: {"view_artifacts"},
}


# ── Request / Response schemas ───────────────────────────────────────────

class AgentRegistration(BaseModel):
    """Payload to onboard a new agent into the system."""

    agent_id: str = Field(..., description="Unique identifier for the agent")
    agent_name: str = Field(..., description="Human-readable name")
    role: AgentRole = Field(default=AgentRole.OBSERVER, description="RBAC role")
    embedding_config: Optional[Dict] = Field(
        default=None,
        description="Embedding configuration (model_id, dim, etc.)",
    )
    metadata: Dict = Field(default_factory=dict)


class PermissionCheckRequest(BaseModel):
    """Check whether an agent may perform an action or lifecycle transition."""

    agent_id: str
    action: Optional[str] = Field(
        default=None,
        description="Action name, e.g. 'run_pipeline'",
    )
    transition: Optional[str] = Field(
        default=None,
        description="Lifecycle transition, e.g. 'INIT→EMBEDDING'",
    )


class PermissionCheckResponse(BaseModel):
    """Result of a permission check."""

    agent_id: str
    allowed: bool
    role: AgentRole
    reason: str = ""


class OnboardingResult(BaseModel):
    """Result returned after successful agent onboarding."""

    agent_id: str
    agent_name: str
    role: AgentRole
    permissions: List[str]
    actions: List[str]
    onboarded: bool = True


class AgentRecord(BaseModel):
    """Internal record for a registered agent."""

    agent_id: str
    agent_name: str
    role: AgentRole
    embedding_config: Optional[Dict] = None
    metadata: Dict = Field(default_factory=dict)
    active: bool = True


class RBACTokenIssueRequest(BaseModel):
    """Issue a signed RBAC access token for MCP client handshakes."""

    subject: str = Field(..., min_length=1)
    tenant_id: str = Field(..., min_length=1)
    client_id: str = Field(..., min_length=1)
    avatar_id: str = Field(..., min_length=1)
    roles: List[str] = Field(default_factory=list)
    scopes: List[str] = Field(default_factory=list)
    tools: List[str] = Field(default_factory=list)
    ttl_seconds: int = Field(default=900, ge=60, le=3600)


class RBACTokenIssueResponse(BaseModel):
    """Response payload for RBAC token issuance."""

    token_type: str = "Bearer"
    access_token: str
    expires_at: int
    expires_in: int
    fingerprint: str
    claims: Dict[str, Any]


class RBACTokenIntrospectRequest(BaseModel):
    """Token introspection request payload."""

    access_token: str = Field(..., min_length=1)


class RBACTokenIntrospectResponse(BaseModel):
    """Token introspection response payload."""

    active: bool
    claims: Dict[str, Any] = Field(default_factory=dict)
    reason: str = ""
