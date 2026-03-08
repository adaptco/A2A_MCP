"""Contracts for authenticated A2A/MCP handshake exchange."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


class RbacClaimProposal(BaseModel):
    """Structured RBAC claim proposal synthesized for handshake exchange."""

    tenant_id: str = Field(..., min_length=1)
    client_id: str = Field(..., min_length=1)
    avatar_id: str = Field(..., min_length=1)
    roles: list[str] = Field(default_factory=list)
    scopes: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    ttl_seconds: int = Field(default=900, ge=60, le=3600)
    reason: str = Field(default="")
    source: str = Field(default="openai-codex")


class RbacAccessTokenClaims(BaseModel):
    """JWT claim envelope issued by the RBAC authority."""

    iss: str = Field(..., min_length=1)
    sub: str = Field(..., min_length=1)
    aud: str = Field(..., min_length=1)
    tenant_id: str = Field(..., min_length=1)
    client_id: str = Field(..., min_length=1)
    avatar_id: str = Field(..., min_length=1)
    roles: list[str] = Field(default_factory=list)
    scopes: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    iat: int = Field(..., ge=0)
    exp: int = Field(..., ge=0)
    jti: str = Field(..., min_length=1)


class A2AHandshakeEnvelope(BaseModel):
    """Stateful handshake envelope shared with clients."""

    handshake_id: str = Field(..., min_length=1)
    status: Literal["initialized", "exchanged", "finalized", "failed"] = "initialized"
    tenant_id: str = Field(default="default")
    client_id: str = Field(..., min_length=1)
    avatar_id: str = Field(..., min_length=1)
    claim_proposal: RbacClaimProposal | None = None
    rbac_token_ref: str | None = None
    rbac_token_fingerprint: str | None = None
    gemini_token_ref: str | None = None
    gemini_token_fingerprint: str | None = None
    world_model_hash: str | None = None
    capability_scores: dict[str, float] = Field(default_factory=dict)
    capabilities: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

