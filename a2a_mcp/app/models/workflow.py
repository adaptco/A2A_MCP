from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class WorkflowNode(BaseModel):
    id: str
    action_id: str
    depends_on: list[str] = Field(default_factory=list)
    inputs: dict[str, Any] | None = None


class WorkflowGate(BaseModel):
    after: str
    type: str = "human_approval"
    policy: str


class WorkflowDAG(BaseModel):
    workflow_id: str
    version: str
    nodes: list[WorkflowNode]
    gates: list[WorkflowGate] = Field(default_factory=list)
    rollback: list[dict[str, Any]] = Field(default_factory=list)
