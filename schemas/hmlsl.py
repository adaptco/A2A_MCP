from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class HMLSLNode(BaseModel):
    """Base node for the Hierarchical Multi-Layered Semantic Ledger."""
    id: str = Field(default_factory=lambda: f"node-{uuid.uuid4().hex[:8]}")
    type: str
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    integrity_hash: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class StructuralNode(HMLSLNode):
    """Definitions of MCP tool contracts and A2A protocols."""
    contract_type: str  # e.g., "MCP_TOOL", "A2A_PROTOCOL"
    definition: Dict[str, Any]


class BehavioralTraceNode(HMLSLNode):
    """Step-by-step logs of reasoning cycles and tool invocations."""
    step_description: str
    tool_invocation: Optional[Dict[str, Any]] = None
    reasoning_trace: Optional[str] = None
    result: Optional[Any] = None


class SemanticWeightNode(HMLSLNode):
    """
    Metadata tagging traces with Resonance scores and Manifold Coordinates.
    """
    target_node_id: str
    resonance_score: float  # Intensity of focus (0.0 - 1.0)
    manifold_coordinates: List[float]  # Latent space vector


class VisualPersonaNode(HMLSLNode):
    """Links semantic clusters to aesthetic parameters for Avatar."""
    cluster_id: str
    aesthetic_params: Dict[str, Any]
    visual_embedding: Optional[List[float]] = None


class RBACNode(HMLSLNode):
    """Self-assigned Role-Based Access Control tokens."""
    role: str
    permissions: List[str]
    justification: str  # Why this role was assigned


class MerkleProof(BaseModel):
    root_hash: str
    proof_nodes: List[str]


class HMLSLArtifact(BaseModel):
    """The complete Hierarchical Multi-Layered Semantic Ledger artifact."""
    model_config = ConfigDict(populate_by_name=True)

    context: str = Field(default="https://schema.org", alias="@context")
    id: str = Field(alias="@id")
    type: str = Field(default="HMLSLArtifact", alias="@type")

    structural_nodes: List[StructuralNode] = Field(default_factory=list)
    behavioral_traces: List[BehavioralTraceNode] = Field(default_factory=list)
    semantic_weights: List[SemanticWeightNode] = Field(default_factory=list)
    visual_persona_nodes: List[VisualPersonaNode] = Field(default_factory=list)
    rbac_nodes: List[RBACNode] = Field(default_factory=list)

    merkle_root: Optional[str] = None
    system_invariants: List[str] = Field(default_factory=list)
