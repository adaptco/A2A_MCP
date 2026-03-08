from __future__ import annotations

from pydantic import BaseModel, Field


class ExecutionContext(BaseModel):
    run_id: str
    step_id: str
    actor: dict[str, str] = Field(default_factory=dict)
    budgets: dict[str, float] = Field(default_factory=dict)
    approvals: dict[str, str] = Field(default_factory=dict)


class ActionRequest(BaseModel):
    request_id: str
    action_id: str
    inputs: dict[str, object] = Field(default_factory=dict)
    context: ExecutionContext
