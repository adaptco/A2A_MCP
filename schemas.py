
from pydantic import BaseModel, Field
from enum import Enum
import uuid
from typing import Optional

class AgentLifecycleState(str, Enum):
    """Enumeration of the agent's lifecycle states."""
    INITIAL = "INITIAL"
    EMBEDDING = "EMBEDDING"
    RAG_QUERY = "RAG_QUERY"
    LORA_ADAPT = "LORA_ADAPT"
    TRAINED = "TRAINED"
    FAILED = "FAILED"

class LoRAConfig(BaseModel):
    """Configuration for a LoRA training job."""
    lora_r: int = 8
    lora_alpha: int = 16
    lora_dropout: float = 0.05
    training_samples: int = 0
    instruction_prompt: str = "Adapt to the user's recovery style."

class ModelArtifact(BaseModel):
    """Represents a model artifact being tracked through the lifecycle."""
    artifact_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    model_id: str = "sentence-transformers/all-mpnet-base-v2"
    embedding_dim: int = 768
    state: AgentLifecycleState = AgentLifecycleState.INITIAL
    lora_config: Optional[LoRAConfig] = None
