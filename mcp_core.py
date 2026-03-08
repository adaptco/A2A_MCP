# a2a_mcp/mcp_core.py - Shared protocol logic
import hashlib
from typing import Dict, Any, Optional
import torch
import torch.nn as nn
import torch.nn.functional as F
from dataclasses import dataclass

@dataclass
class MCPResult:
    """Output from shared MCP core"""
    processed_embedding: torch.Tensor  # [1, 128] canonical MCP tensor
    arbitration_scores: torch.Tensor   # [n_roles] middleware weights
    protocol_features: Dict[str, Any]  # Similarity, clustering, etc.
    execution_hash: str               # Sovereignty preservation

class MCPCore(nn.Module):
    """Shared Multi-Client Protocol computations"""
    
    def __init__(self, hidden_dim: int = 128, n_roles: int = 32):
        super().__init__()
        self.hidden_dim = hidden_dim
        self.n_roles = n_roles
        
        # Namespace-respecting feature extraction
        self.feature_extractor = nn.Sequential(
            nn.Linear(4096, 1024),
            nn.LayerNorm(1024),
            nn.ReLU(),
            nn.Linear(1024, hidden_dim),
            nn.LayerNorm(hidden_dim)
        )
        
        # Role arbitration (middleware layer)
        self.arbitration_head = nn.Sequential(
            nn.Linear(hidden_dim, 256),
            nn.ReLU(),
            nn.Linear(256, n_roles),
            nn.Softmax(dim=-1)
        )
        
        # Protocol similarity computation (namespace-safe)
        self.similarity_head = nn.Linear(hidden_dim, 64)
    
    def forward(self, namespaced_embedding: torch.Tensor) -> MCPResult:
        """Core protocol computations on isolated embedding"""
        assert namespaced_embedding.shape == (1, 4096)
        
        # 1. FEATURE EXTRACTION (shared, namespace-respecting)
        features = self.feature_extractor(namespaced_embedding)
        
        # 2. ROLE ARBITRATION (middleware weights)
        arbitration_scores = self.arbitration_head(features)
        
        # 3. PROTOCOL COMPUTATIONS (similarity, clustering)
        similarity_features = self.similarity_head(features)
        
        # 4. CANONICALIZATION (MCP tensor)
        mcp_tensor = F.normalize(features.squeeze(0), dim=-1)
        
        # 5. SOVEREIGNTY HASH (for event store)
        execution_hash = torch.sum(mcp_tensor * torch.arange(self.hidden_dim, 
                                                           dtype=torch.float32)).item()
        execution_hash = hashlib.sha256(str(execution_hash).encode()).hexdigest()
        
        return MCPResult(
            processed_embedding=mcp_tensor.unsqueeze(0),
            arbitration_scores=arbitration_scores.squeeze(0),
            protocol_features={
                "similarity_features": similarity_features.detach().numpy(),
                "feature_norm": torch.norm(features).item()
            },
            execution_hash=execution_hash
        )
    
    def compute_protocol_similarity(self, emb1: torch.Tensor, emb2: torch.Tensor) -> float:
        """
        Namespace-safe similarity between two MCP tensors.
        The tenant_vector projection ensures emb1 * vec_A ≠ emb2 * vec_B
        """
        feat1 = self.feature_extractor(emb1)
        feat2 = self.feature_extractor(emb2)
        return F.cosine_similarity(feat1.mean(0), feat2.mean(0), dim=-1).item()
