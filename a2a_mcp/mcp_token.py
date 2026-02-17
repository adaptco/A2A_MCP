from dataclasses import dataclass
from typing import Dict, List, Optional
import torch

@dataclass
class MCPToken:
    """
    Agent-to-Agent Middleware Control Plane Token.
    
    Attributes:
        token_id (str): Unique identifier for the token.
        embedding (torch.Tensor): [seq_len, hidden_dim] flattened logic.
        phase_diagram (torch.Tensor): [n_roles, middleware_dim] phase space mapping.
        arbitration_scores (torch.Tensor): [n_agents] priority scores.
        lora_weights (Dict[str, torch.Tensor]): Synthesized skill weights.
        metadata (Dict): Provenance and tracking metadata.
    """
    token_id: str
    embedding: torch.Tensor
    phase_diagram: torch.Tensor
    arbitration_scores: torch.Tensor
    lora_weights: Dict[str, torch.Tensor]
    metadata: Dict
