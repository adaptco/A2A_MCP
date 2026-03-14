from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from enum import Enum
from datetime import datetime
from .agent_artifacts import MCPArtifact

class AgentLifecycleState(str, Enum):
    """Simulated state space for agent lifecycle."""
    INIT = "INIT"
    EMBEDDING = "EMBEDDING"
    RAG_QUERY = "RAG_QUERY"
    LORA_ADAPT = "LORA_ADAPT"
    HEALING = "HEALING"
    CONVERGED = "CONVERGED"
    FAILED = "FAILED"
    SCORE_FINALIZED = "SCORE_FINALIZED"
    HANDSHAKE = "HANDSHAKE"

STATE_TRANSITIONS: Dict[AgentLifecycleState, List[AgentLifecycleState]] = {
    AgentLifecycleState.HANDSHAKE: [AgentLifecycleState.INIT, AgentLifecycleState.FAILED],
    AgentLifecycleState.INIT: [AgentLifecycleState.EMBEDDING],
    AgentLifecycleState.EMBEDDING: [AgentLifecycleState.RAG_QUERY, AgentLifecycleState.FAILED],
    AgentLifecycleState.RAG_QUERY: [AgentLifecycleState.LORA_ADAPT, AgentLifecycleState.FAILED],
    AgentLifecycleState.LORA_ADAPT: [AgentLifecycleState.HEALING, AgentLifecycleState.FAILED],
    AgentLifecycleState.HEALING: [AgentLifecycleState.CONVERGED, AgentLifecycleState.LORA_ADAPT, AgentLifecycleState.FAILED],
    AgentLifecycleState.CONVERGED: [],  # Terminal
    AgentLifecycleState.FAILED: [AgentLifecycleState.INIT],  # Rollback to INIT
    AgentLifecycleState.SCORE_FINALIZED: [], # Terminal for gaming
}

class LoRAConfig(BaseModel):
    r: int = 8
    lora_alpha: int = 32
    target_modules: List[str] = ["q_proj", "v_proj"]
    lora_dropout: float = 0.05
    bias: str = "none"
    task_type: str = "CAUSAL_LM"

class ModelArtifact(MCPArtifact):
    # Core fields
    artifact_id: str = Field(default_factory=lambda: f"art-{datetime.utcnow().timestamp()}")
    model_id: str = Field(..., description="HuggingFace model identifier")
    weights_hash: str = Field(..., description="SHA256 of model weights")
    embedding_dim: int = Field(..., description="Embedding dimension")
    category: str = Field(default="mlops", description="Event category: mlops, gaming")
    
    # Lifecycle
    state: AgentLifecycleState = Field(default=AgentLifecycleState.HANDSHAKE)
    parent_artifact_id: Optional[str] = None
    agent_name: str = Field(default="ModelRegistry")
    version: str = Field(default="1.0.0")
    
    # LoRA
    lora_config: Optional[LoRAConfig] = None
    
    # Default overrides
    type: str = Field(default="model_artifact")
    content: str = Field(default="", description="Serialized model config or description")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def can_transition_to(self, target: AgentLifecycleState) -> bool:
        return target in STATE_TRANSITIONS.get(self.state, [])

    def transition(self, target: AgentLifecycleState) -> "ModelArtifact":
        """
        Transition to a new state if valid.
        Returns a new artifact with updated state (immutable pattern).
        """
        if not self.can_transition_to(target):
            raise ValueError(
                f"Invalid transition: {self.state.value} -> {target.value}. "
                f"Valid targets: {[s.value for s in STATE_TRANSITIONS.get(self.state, [])]}"
            )
        
        # Create new instance (immutable)
        return self.model_copy(update={
            "state": target,
            "parent_artifact_id": self.artifact_id,
            "timestamp": datetime.utcnow().isoformat()
        })
