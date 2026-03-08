from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class PlanAction(BaseModel):
    action_id: str
    title: str
    instruction: str
    status: Literal["pending", "in_progress", "completed", "failed"] = "pending"
    validation_feedback: Optional[str] = None
    metadata: Dict[str, str] = Field(default_factory=dict)


class ProjectPlan(BaseModel):
    plan_id: str
    project_name: str
    requester: str
    actions: List[PlanAction] = Field(default_factory=list)
