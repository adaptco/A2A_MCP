from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class PlanAction(BaseModel):
    action_id: str
    title: str
    instruction: str
    metadata: Optional[Dict[str, Any]] = None

class ProjectPlan(BaseModel):
    plan_id: str
    project_name: str
    requester: str
    actions: List[PlanAction]
    status: str = "pending"