"""Shared MCP core computations with tenant-safe embedding processing."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Dict

import torch
import torch.nn as nn
import torch.nn.functional as F


@dataclass
class MCPResult:
    """Output from shared MCP core."""

    processed_embedding: torch.Tensor  # [1, hidden_dim]
    arbitration_scores: torch.Tensor  # [n_roles]
    protocol_features: Dict[str, Any]
    execution_hash: str


def namespace_project_embedding(
    raw_embedding: torch.Tensor, tenant_vector: torch.Tensor
) -> torch.Tensor:
    """
    Apply tenant namespace projection to prevent cross-tenant embedding collisions.

    Args:
        raw_embedding: Tensor with shape [1, D] (or [D])
        tenant_vector: Tensor with shape [D]

    Returns:
        Namespaced embedding tensor with shape [1, D].
    """
    if raw_embedding.dim() == 1:
        raw_embedding = raw_embedding.unsqueeze(0)
    if raw_embedding.dim() != 2 or raw_embedding.shape[0] != 1:
        raise ValueError("raw_embedding must have shape [1, D] or [D]")
    if tenant_vector.dim() != 1:
        raise ValueError("tenant_vector must have shape [D]")
    if raw_embedding.shape[1] != tenant_vector.shape[0]:
        raise ValueError("tenant_vector dimensionality must match raw_embedding width")

    tenant_vector = F.normalize(tenant_vector, dim=0)
    projected = raw_embedding * tenant_vector.unsqueeze(0)
    return projected


class MCPCore(nn.Module):
    """Shared Multi-Client Protocol computations."""

    def __init__(
        self,
        input_dim: int = 4096,
        hidden_dim: int = 128,
        n_roles: int = 32,
    ) -> None:
        super().__init__()
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.n_roles = n_roles

        self.feature_extractor = nn.Sequential(
            nn.Linear(input_dim, 1024),
            nn.LayerNorm(1024),
            nn.ReLU(),
            nn.Linear(1024, hidden_dim),
            nn.LayerNorm(hidden_dim),
        )

        self.arbitration_head = nn.Sequential(
            nn.Linear(hidden_dim, 256),
            nn.ReLU(),
            nn.Linear(256, n_roles),
            nn.Softmax(dim=-1),
        )

        self.similarity_head = nn.Linear(hidden_dim, 64)
        self.register_buffer(
            "_hash_weights",
            torch.arange(hidden_dim, dtype=torch.float32),
            persistent=False,
        )

    def forward(self, namespaced_embedding: torch.Tensor) -> MCPResult:
        """Run core protocol computations on a namespaced embedding."""
        if namespaced_embedding.shape != (1, self.input_dim):
            raise ValueError(
                f"Expected namespaced embedding shape (1, {self.input_dim}), "
                f"got {tuple(namespaced_embedding.shape)}"
            )

        features = self.feature_extractor(namespaced_embedding)
        arbitration_scores = self.arbitration_head(features)
        similarity_features = self.similarity_head(features)
        mcp_tensor = F.normalize(features.squeeze(0), dim=-1)

        hash_weights = self._hash_weights.to(device=mcp_tensor.device, dtype=mcp_tensor.dtype)
        hash_scalar = torch.sum(mcp_tensor * hash_weights).item()
        execution_hash = hashlib.sha256(f"{hash_scalar:.12f}".encode("utf-8")).hexdigest()

        return MCPResult(
            processed_embedding=mcp_tensor.unsqueeze(0),
            arbitration_scores=arbitration_scores.squeeze(0),
            protocol_features={
                "similarity_features": similarity_features.detach().cpu().tolist(),
                "feature_norm": float(torch.norm(features).item()),
            },
            execution_hash=execution_hash,
        )

    def compute_protocol_similarity(
        self, emb1: torch.Tensor, emb2: torch.Tensor
    ) -> float:
        """Compute namespace-safe cosine similarity between two namespaced embeddings."""
        if emb1.shape != (1, self.input_dim) or emb2.shape != (1, self.input_dim):
            raise ValueError(
                f"Both embeddings must have shape (1, {self.input_dim})"
            )
        feat1 = self.feature_extractor(emb1)
        feat2 = self.feature_extractor(emb2)
        return float(F.cosine_similarity(feat1.squeeze(0), feat2.squeeze(0), dim=-1).item())


__all__ = ["MCPResult", "MCPCore", "namespace_project_embedding"]
