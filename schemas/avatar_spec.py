from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AvatarPolicy(BaseModel):
    allow_tools: List[str] = Field(default_factory=list)
    deny_tools: List[str] = Field(default_factory=list)
    max_iterations: int = 5
    egress_rules: List[str] = Field(default_factory=list)


class AvatarKnowledgeSubstrate(BaseModel):
    rag_collections: List[str] = Field(default_factory=list)
    structured_stores: List[str] = Field(default_factory=list) # e.g. "bom_graph", "process_graph"


class AvatarSpec(BaseModel):
    """
    Declarative specification for an 'Avatar-as-Code' bundle.
    """
    name: str
    version: str = Field(..., pattern=r"^v?[0-9]+(\.[0-9]+)*$")
    role: str
    capabilities: List[str] = Field(default_factory=list)
    
    policy: AvatarPolicy
    knowledge: AvatarKnowledgeSubstrate
    
    verification_harness: Dict[str, Any] = Field(
        default_factory=lambda: {
            "golden_tasks": [],
            "safety_checks": [],
            "regression_tests": []
        }
    )
    
    metadata: Dict[str, Any] = Field(default_factory=dict)
