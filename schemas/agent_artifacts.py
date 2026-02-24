from pydantic import BaseModel
from typing import Dict, Any, Optional

class MCPArtifact(BaseModel):
    artifact_id: str
    type: str
    content: str
    metadata: Optional[Dict[str, Any]] = None