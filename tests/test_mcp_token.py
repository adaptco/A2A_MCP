import torch
import pytest
from a2a_mcp.mcp_token import MCPToken
from typing import Dict

def test_mcp_token_instantiation():
    """
    Tests basic creation of the MCPToken and attribute assignment.
    """
    token_id = "test-token-id-123"
    embedding = torch.randn(10, 512)
    phase_diagram = torch.randn(8, 128)
    arbitration_scores = torch.randn(20)
    lora_weights = {"attention": torch.randn(4, 4)}
    metadata = {"source": "test_mcp_token", "version": "1.0"}

    token = MCPToken(
        token_id=token_id,
        embedding=embedding,
        phase_diagram=phase_diagram,
        arbitration_scores=arbitration_scores,
        lora_weights=lora_weights,
        metadata=metadata,
    )

    assert isinstance(token, MCPToken)
    assert token.token_id == token_id
    assert torch.equal(token.embedding, embedding)
    assert torch.equal(token.phase_diagram, phase_diagram)
    assert torch.equal(token.arbitration_scores, arbitration_scores)
    assert token.lora_weights == lora_weights
    assert token.metadata == metadata

def test_mcp_token_attribute_types():
    """
    Verifies that the attributes of an instantiated MCPToken have the correct types.
    """
    # Create a token with minimal but type-correct data
    token = MCPToken(
        token_id="dummy-id",
        embedding=torch.tensor([]),
        phase_diagram=torch.tensor([]),
        arbitration_scores=torch.tensor([]),
        lora_weights={},
        metadata={},
    )

    assert isinstance(token.token_id, str)
    assert isinstance(token.embedding, torch.Tensor)
    assert isinstance(token.phase_diagram, torch.Tensor)
    assert isinstance(token.arbitration_scores, torch.Tensor)
    assert isinstance(token.lora_weights, Dict)
    assert isinstance(token.metadata, Dict)

def test_mcp_token_empty_and_optional_fields():
    """
    Tests that the MCPToken can be created with empty or default-like values.
    """
    token = MCPToken(
        token_id="",
        embedding=torch.empty(0),
        phase_diagram=torch.empty(0, 0),
        arbitration_scores=torch.empty(0),
        lora_weights={},
        metadata={},
    )
    
    assert token.token_id == ""
    assert token.embedding.numel() == 0
    assert token.phase_diagram.numel() == 0
    assert token.arbitration_scores.numel() == 0
    assert token.lora_weights == {}
    assert token.metadata == {}
