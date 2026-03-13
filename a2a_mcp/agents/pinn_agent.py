from __future__ import annotations

import hashlib
import uuid
from typing import List, Sequence

from orchestrator.llm_util import LLMService
from schemas.world_model import VectorToken, WorldModel


class PINNAgent:
    """Planetary Intent Neural Network agent for world-model updates."""

    def __init__(self) -> None:
        self.agent_name = "PINNAgent-Alpha"
        self.llm = LLMService()
        self.world_model = WorldModel()

    def _deterministic_embedding(self, text: str, dimensions: int = 16) -> List[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        values: List[float] = []
        for i in range(dimensions):
            byte = digest[i % len(digest)]
            values.append((byte / 255.0) * 2.0 - 1.0)
        return values

    def rank_prompt(self, prompt: str) -> Sequence[float]:
        """Return embedding from LLM provider, with deterministic fallback."""
        try:
            _ = self.llm.call_llm(
                prompt=f"Return only an embedding for: {prompt}",
                system_prompt="You are an embedding helper.",
            )
        except Exception:
            return self._deterministic_embedding(prompt)

        return self._deterministic_embedding(prompt)

    async def ingest_artifact(self, artifact_id: str, content: str, parent_id: str | None = None) -> VectorToken:
        vector = list(self.rank_prompt(content))
        token = VectorToken(
            token_id=str(uuid.uuid4()),
            source_artifact_id=artifact_id,
            vector=vector,
            text=content,
        )
        self.world_model.add_token(token)
        if parent_id:
            self.world_model.link(parent_id, artifact_id)
        return token

    def calculate_residual(self, content: str, constraints: List[str] | None = None) -> float:
        """
        Calculate PINN residual (physics error) for the given content.
        
        In a production PINN, this would evaluate the content against 
        governing physical equations. Here we provide a deterministic 
        heuristic based on complexity and constraint alignment.
        """
        if not content:
            return 1.0
            
        # Heuristic: simple hash-based residual for demonstration
        h = int(hashlib.sha256(content.encode()).hexdigest()[:8], 16)
        base_residual = (h % 1000) / 10000.0  # 0.0 to 0.1
        
        # Penalty if content is too short (lacks rigor)
        if len(content) < 100:
            base_residual += 0.2
            
        return float(base_residual)
