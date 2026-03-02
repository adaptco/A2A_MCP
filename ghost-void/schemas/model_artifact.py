"""
Model Artifact Schema
Extends MCPArtifact with model-specific fields for CI/CD traceability.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from enum import Enum


class AgentLifecycleState(str, Enum):
    """Simulated state space for agent lifecycle."""
    INIT = "INIT"
    EMBEDDING = "EMBEDDING"
    RAG_QUERY = "RAG_QUERY"
    LORA_ADAPT = "LORA_ADAPT"
    HEALING = "HEALING"
    CONVERGED = "CONVERGED"
    FAILED = "FAILED"


# Valid state transitions
STATE_TRANSITIONS: Dict[AgentLifecycleState, List[AgentLifecycleState]] = {
    AgentLifecycleState.INIT: [AgentLifecycleState.EMBEDDING],
    AgentLifecycleState.EMBEDDING: [AgentLifecycleState.RAG_QUERY, AgentLifecycleState.FAILED],
    AgentLifecycleState.RAG_QUERY: [AgentLifecycleState.LORA_ADAPT, AgentLifecycleState.FAILED],
    AgentLifecycleState.LORA_ADAPT: [AgentLifecycleState.HEALING, AgentLifecycleState.FAILED],
    AgentLifecycleState.HEALING: [AgentLifecycleState.CONVERGED, AgentLifecycleState.LORA_ADAPT, AgentLifecycleState.FAILED],
    AgentLifecycleState.CONVERGED: [],  # Terminal
    AgentLifecycleState.FAILED: [AgentLifecycleState.INIT],  # Rollback to INIT
}


class LoRAConfig(BaseModel):
    """LoRA adaptation configuration."""
    rank: int = Field(default=8, description="LoRA rank")
    alpha: float = Field(default=16.0, description="LoRA alpha scaling factor")
    target_modules: List[str] = Field(default_factory=lambda: ["q_proj", "v_proj"])
    training_samples: int = Field(default=0, description="Number of training samples used")


class ModelArtifact(BaseModel):
    """
    Model-as-artifact schema with cryptographic anchors.
    Extends the MCPArtifact contract for model lifecycle tracking.
    """
    artifact_id: str = Field(..., description="Unique UUID")
    model_id: str = Field(..., description="HuggingFace model identifier")
    weights_hash: str = Field(..., description="SHA256 of model weights")
    embedding_dim: int = Field(..., description="Embedding dimension")
    
    # Lifecycle
    state: AgentLifecycleState = Field(default=AgentLifecycleState.INIT)
    parent_artifact_id: Optional[str] = None
    agent_name: str = Field(default="ModelRegistry")
    version: str = Field(default="1.0.0")
    
    # LoRA
    lora_config: Optional[LoRAConfig] = None
    
    # Metadata
    type: str = Field(default="model_artifact")
    content: str = Field(default="", description="Serialized model config or description")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def can_transition_to(self, target: AgentLifecycleState) -> bool:
        """Check if a state transition is valid."""
        return target in STATE_TRANSITIONS.get(self.state, [])

    def transition(self, target: AgentLifecycleState) -> "ModelArtifact":
        """
        Transition to a new state if valid.
        Returns a new artifact with updated state (immutable pattern).
        """
        if not self.can_transition_to(target):
            raise ValueError(
                f"Invalid transition: {self.state.value} → {target.value}. "
                f"Valid targets: {[s.value for s in STATE_TRANSITIONS.get(self.state, [])]}"
            )
        
        return self.model_copy(update={
            "state": target,
            "parent_artifact_id": self.artifact_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
