"""Runtime scenario envelope contracts for A2A MCP integration."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Literal

from pydantic import BaseModel, Field


class ProjectionMetadata(BaseModel):
    """Provenance for deterministic embedding projection."""

    source_dim: int = Field(..., ge=1)
    target_dim: int = Field(default=1536, ge=1)
    method: str = Field(..., min_length=1)
    seed: str = Field(..., min_length=1)


class ScenarioTraceRecord(BaseModel):
    """Scenario event emitted during synthesis."""

    stage: str = Field(..., min_length=1)
    event_type: str = Field(..., min_length=1)
    payload: Dict[str, Any] = Field(default_factory=dict)


class RetrievalChunk(BaseModel):
    """Chunk-level retrieval result with provenance."""

    chunk_id: str = Field(..., min_length=1)
    text: str = Field(..., min_length=1)
    score: float
    embedding_hash: str = Field(..., min_length=1)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RetrievalContext(BaseModel):
    """Retrieval package attached to a scenario envelope."""

    query_hash: str = ""
    chunks: List[RetrievalChunk] = Field(default_factory=list)
    provenance: Dict[str, Any] = Field(default_factory=dict)


class LoRACandidate(BaseModel):
    """Instruction/output candidate for LoRA adaptation."""

    instruction: str = Field(..., min_length=1)
    output: str = Field(..., min_length=1)
    source_chunk_id: str = Field(..., min_length=1)
    provenance_hash: str = Field(..., min_length=1)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RuntimeScenarioEnvelope(BaseModel):
    """Canonical runtime scenario envelope for cross-plane integration."""

    schema_version: str = Field(default="1.0")
    tenant_id: str = Field(..., min_length=1)
    execution_id: str = Field(..., min_length=1)
    runtime_state: Dict[str, Any] = Field(default_factory=dict)
    scenario_trace: List[ScenarioTraceRecord] = Field(default_factory=list)
    retrieval_context: RetrievalContext = Field(default_factory=RetrievalContext)
    lora_candidates: List[LoRACandidate] = Field(default_factory=list)
    embedding_dim: Literal[16, 768, 1536] = 1536
    hash_prev: str = ""
    hash_current: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    projection_metadata: ProjectionMetadata | None = None

    def hash_payload(self) -> Dict[str, Any]:
        """Return payload used for deterministic lineage hashing."""
        return {
            "schema_version": self.schema_version,
            "tenant_id": self.tenant_id,
            "execution_id": self.execution_id,
            "runtime_state": self.runtime_state,
            "scenario_trace": [record.model_dump(mode="json") for record in self.scenario_trace],
            "retrieval_context": self.retrieval_context.model_dump(mode="json"),
            "lora_candidates": [candidate.model_dump(mode="json") for candidate in self.lora_candidates],
            "embedding_dim": self.embedding_dim,
            "timestamp": self.timestamp,
            "projection_metadata": (
                self.projection_metadata.model_dump(mode="json")
                if self.projection_metadata
                else None
            ),
        }
