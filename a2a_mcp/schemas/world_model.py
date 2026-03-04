from __future__ import annotations

from datetime import datetime
from typing import Dict, List

from pydantic import BaseModel, Field


class VectorToken(BaseModel):
    """A semantic vector representation for an artifact or prompt segment."""

    token_id: str
    source_artifact_id: str
    vector: List[float]
    text: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class WorldModel(BaseModel):
    """Unified semantic memory maintained by the PINN agent."""

    model_id: str = "global-world-model"
    knowledge_graph: Dict[str, List[str]] = Field(default_factory=dict)
    vector_tokens: Dict[str, VectorToken] = Field(default_factory=dict)

    def link(self, source_id: str, target_id: str) -> None:
        self.knowledge_graph.setdefault(source_id, [])
        if target_id not in self.knowledge_graph[source_id]:
            self.knowledge_graph[source_id].append(target_id)

    def add_token(self, token: VectorToken) -> None:
        self.vector_tokens[token.token_id] = token
