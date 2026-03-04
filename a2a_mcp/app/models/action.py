from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ActionAuth(BaseModel):
    required_scopes: list[str] = Field(default_factory=list)
    oidc_claims: dict[str, Any] = Field(default_factory=dict)


class ActionPolicy(BaseModel):
    egress: str = "deny_by_default"
    allowed_domains: list[str] = Field(default_factory=list)
    max_payload_kb: int = 128
    requires_approval: str | None = None


class ActionExecution(BaseModel):
    timeout_ms: int = 60000
    retries: int = 2
    idempotency: str = "required"


class ActionDefinition(BaseModel):
    action_id: str = Field(..., pattern=r"^[a-z_]+\.[a-z_]+@\d+$")
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    auth: ActionAuth
    policy: ActionPolicy
    execution: ActionExecution
