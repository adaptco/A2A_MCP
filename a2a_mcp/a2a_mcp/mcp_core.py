"""Shared MCP core computations for namespaced embeddings."""

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

    processed_embedding: torch.Tensor  # [1, hidden_dim] canonical MCP tensor
    arbitration_scores: torch.Tensor  # [n_roles] middleware weights
    protocol_features: Dict[str, Any]  # Similarity, clustering, etc.
    execution_hash: str  # Sovereignty preservation


class MCPCore(nn.Module):
    """Shared Multi-Client Protocol computations."""

    def __init__(self, input_dim: int = 4096, hidden_dim: int = 128, n_roles: int = 32):
        super().__init__()
        self.input_dim = int(input_dim)
        self.hidden_dim = int(hidden_dim)
        self.n_roles = int(n_roles)

        self.feature_extractor = nn.Sequential(
            nn.Linear(self.input_dim, 1024),
            nn.LayerNorm(1024),
            nn.ReLU(),
            nn.Linear(1024, self.hidden_dim),
            nn.LayerNorm(self.hidden_dim),
        )

        self.arbitration_head = nn.Sequential(
            nn.Linear(self.hidden_dim, 256),
            nn.ReLU(),
            nn.Linear(256, self.n_roles),
            nn.Softmax(dim=-1),
        )

        self.similarity_head = nn.Linear(self.hidden_dim, 64)

    def forward(self, namespaced_embedding: torch.Tensor) -> MCPResult:
        """Core protocol computations on isolated embedding."""
        expected_shape = (1, self.input_dim)
        if tuple(namespaced_embedding.shape) != expected_shape:
            raise ValueError(f"Expected namespaced embedding shape {expected_shape}, got {tuple(namespaced_embedding.shape)}")

        features = self.feature_extractor(namespaced_embedding)
        arbitration_scores = self.arbitration_head(features)
        similarity_features = self.similarity_head(features)
        mcp_tensor = F.normalize(features.squeeze(0), dim=-1)

        weighted_sum = torch.sum(
            mcp_tensor
            * torch.arange(self.hidden_dim, dtype=torch.float32, device=mcp_tensor.device)
        ).item()
        execution_hash = hashlib.sha256(f"{weighted_sum:.10f}".encode("utf-8")).hexdigest()

        return MCPResult(
            processed_embedding=mcp_tensor.unsqueeze(0),
            arbitration_scores=arbitration_scores.squeeze(0),
            protocol_features={
                "similarity_features": similarity_features.detach().cpu().tolist(),
                "feature_norm": float(torch.norm(features).item()),
            },
            execution_hash=execution_hash,
        )

    def compute_protocol_similarity(self, emb1: torch.Tensor, emb2: torch.Tensor) -> float:
        """Namespace-safe similarity between two namespaced embeddings."""
        feat1 = self.feature_extractor(emb1)
        feat2 = self.feature_extractor(emb2)
        return float(F.cosine_similarity(feat1.mean(0), feat2.mean(0), dim=-1).item())
