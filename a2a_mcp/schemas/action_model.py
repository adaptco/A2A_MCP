from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class ActionDeterminism(str, Enum):
    DETERMINISTIC = "deterministic"
    STOCHASTIC = "stochastic"


class ActionAuthRequirement(BaseModel):
    required_scopes: List[str] = Field(default_factory=list)
    require_service_signature: bool = True
    oidc_allowlist: Optional[List[str]] = None


class ActionActionModel(BaseModel):
    """
    The universal contract for any callable workflow step.
    Aligns MCP tools, orchestrator steps, and deployment ops.
    """
    action_id: str = Field(..., pattern=r"^[a-z0-9_]+\.[a-z0-9_]+@v[0-9]+(\.[0-9]+)*$")
    description: str
    
    # Validation
    input_schema: Dict[str, Any]  # JSON Schema
    output_schema: Dict[str, Any] # JSON Schema
    
    # Execution Rules
    determinism: ActionDeterminism = ActionDeterminism.DETERMINISTIC
    timeout_seconds: int = 30
    cost_budget_tokens: Optional[int] = None
    
    # Security
    auth: ActionAuthRequirement = Field(default_factory=ActionAuthRequirement)
    
    # Audit & Replay
    is_replayable: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("action_id")
    @classmethod
    def validate_action_id(cls, v: str) -> str:
        # Example format: orchestrator.generate_code@v1.0.0
        return v
