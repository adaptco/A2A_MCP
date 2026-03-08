from pydantic import BaseModel, Field
from typing import Literal, Optional, Dict, Any, List

ActionType = Literal["continue", "revise", "refuse", "request_info", "drive", "reset", "idle", "jump", "left", "right"]

class ParkerDecision(BaseModel):
    action: ActionType
    rationale: str = Field(..., min_length=1)
    confidence: float = Field(..., ge=0.0, le=1.0)

    # Optional structured knobs for training
    next_prompt: Optional[str] = None
    tags: List[str] = []
    metrics: Dict[str, float] = {}
    patch_plan: Optional[Dict[str, Any]] = None  # e.g., files_to_edit, steps
    
    # Specific to ghost void locomotion
    velocity: Optional[float] = None
    steering: Optional[float] = None
