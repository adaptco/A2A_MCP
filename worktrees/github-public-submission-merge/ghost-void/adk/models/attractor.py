from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from uuid import UUID

class FeatureAttractor(BaseModel):
    """
    Python representation of the Feature Attractor schema.
    Used by the Data Analyst agent to rerank vector search results.
    """
    id: UUID = Field(..., description="Unique identifier for the attractor.")
    name: str = Field(..., description="Marketing name of the feature.")
    description: str = Field(..., description="Detailed description of the desired user experience.")
    vector_queries: List[str] = Field(..., min_items=1, description="Keywords for vector ranking.")
    target_personalities: Optional[List[str]] = Field(default=None, description="Target Avatar styles.")
    physics_bounds: Optional[Dict[str, float]] = Field(default=None, description="Physical constraints.")
    priority: float = Field(..., ge=0.0, le=1.0, description="Importance weight.")

    class Config:
        schema_extra = {
            "example": {
                "id": "12345678-1234-5678-1234-567812345678",
                "name": "Supra Drift Mode",
                "description": "High-angle drifting physics.",
                "vector_queries": ["drift", "oversteer", "tire slip"],
                "target_personalities": ["Driver", "Engineer"],
                "physics_bounds": {"slip_angle_max": 45.0},
                "priority": 0.95
            }
        }
