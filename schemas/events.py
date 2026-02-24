from pydantic import BaseModel
from typing import Dict, Any, Optional

class EventMetadata(BaseModel):
    trace_id: str
    source: Optional[str] = None

class EventPayload(BaseModel):
    type: str
    data: Dict[str, Any]

class RuntimeEvent(BaseModel):
    metadata: EventMetadata
    payload: EventPayload