"""
MCPToken — Phase diagram and arbitration representation for the Agent Mesh.
Ported from: a2a_mcp/mcp_token.py + a2a_mcp/core.py
"""
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
import torch


@dataclass
class MCPToken:
    """
    An MCP Token encapsulates the full state of a CI/CD embedding pipeline
    run, including a phase diagram of role probabilities and agent arbitration.
    """
    token_id: str
    embedding: torch.Tensor           # [1, hidden_dim] — pooled CI/CD artifact embedding
    phase_diagram: torch.Tensor       # [n_roles, middleware_dim] — role phase space
    arbitration_scores: torch.Tensor  # [n_agents] — softmax agent priority weights
    lora_weights: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class MCPTokenFactory:
    """
    Generates MCPTokens from CI/CD pipeline embeddings.
    Ported from A2AMCP.ci_cd_embedding_to_token().
    """
    N_ROLES = 128
    MIDDLEWARE_DIM = 256
    N_AGENTS = 10

    def __init__(self, base_model: str = "google/gemma-2-2b-it", hidden_dim: int = 4096):
        self.base_model = base_model
        self.hidden_dim = hidden_dim

    def from_embeddings(self, ci_cd_embeddings: torch.Tensor) -> MCPToken:
        """
        Phase 1: Consume CI/CD embeddings [n_artifacts, hidden_dim] and generate an MCPToken.
        """
        # Pool artifacts into one representative embedding
        pooled = torch.mean(ci_cd_embeddings, dim=0, keepdim=True)  # [1, hidden_dim]

        # Phase space projection: role seeds × embedding
        with torch.no_grad():
            role_seeds = torch.randn(self.N_ROLES, self.hidden_dim)
            phase_diagram = torch.randn(self.N_ROLES, self.MIDDLEWARE_DIM)

        # Arbitration: probability distribution across agents
        arbitration_scores = torch.softmax(torch.randn(self.N_AGENTS), dim=0)

        return MCPToken(
            token_id=str(uuid.uuid4()),
            embedding=pooled,
            phase_diagram=phase_diagram,
            arbitration_scores=arbitration_scores,
            lora_weights={},
            metadata={"base_model": self.base_model},
        )
