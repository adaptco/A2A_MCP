import pytest
import torch
import torch.nn.functional as F

from a2a_mcp.mcp_core import MCPCore, MCPResult


def test_mcp_core_deterministic_hash():
    """Check that the execution hash is deterministic."""
    core = MCPCore()
    input1 = torch.randn(1, 4096)
    input2 = torch.randn(1, 4096)

    hash1_a = core(input1).execution_hash
    hash1_b = core(input1).execution_hash
    hash2 = core(input2).execution_hash

    assert hash1_a == hash1_b
    assert hash1_a != hash2


def test_mcp_core_raises_for_invalid_shape():
    """Verify ValueError on incorrect input tensor shape."""
    core = MCPCore(input_dim=100, hidden_dim=10, n_roles=5)
    
    # Valid shape should work
    valid_tensor = torch.randn(1, 100)
    core(valid_tensor)

    # Invalid shapes should raise ValueError
    with pytest.raises(ValueError, match="Expected namespaced embedding shape"):
        core(torch.randn(1, 99))
    with pytest.raises(ValueError, match="Expected namespaced embedding shape"):
        core(torch.randn(2, 100))
    with pytest.raises(ValueError, match="Expected namespaced embedding shape"):
        core(torch.randn(100))
    
    # Wrong input_dim should also raise a ValueError
    with pytest.raises(ValueError, match="Expected namespaced embedding shape"):
        core(torch.randn(1, 4096))


def test_mcp_result_data_class():
    processed_embedding = torch.randn(1, 128)
    arbitration_scores = torch.randn(32)
    protocol_features = {"feature_norm": 1.0}
    execution_hash = "test_hash"
    result = MCPResult(
        processed_embedding=processed_embedding,
        arbitration_scores=arbitration_scores,
        protocol_features=protocol_features,
        execution_hash=execution_hash,
    )
    assert result.processed_embedding is processed_embedding
    assert result.arbitration_scores is arbitration_scores
    assert result.protocol_features is protocol_features
    assert result.execution_hash == execution_hash


def test_forward_pass_and_hash_consistency():
    torch.manual_seed(7)
    core = MCPCore(hidden_dim=128, n_roles=32)
    namespaced = torch.randn(1, 4096)

    result1 = core(namespaced)
    result2 = core(namespaced)

    assert torch.allclose(result1.processed_embedding, result2.processed_embedding)
    assert torch.allclose(result1.arbitration_scores, result2.arbitration_scores)
    assert result1.execution_hash == result2.execution_hash


def test_protocol_features():
    """Check the protocol_features dictionary."""
    torch.manual_seed(7)
    core = MCPCore()
    namespaced = torch.randn(1, 4096)

    result = core(namespaced)

    assert isinstance(result.protocol_features, dict)
    assert "similarity_features" in result.protocol_features
    assert "feature_norm" in result.protocol_features
    assert isinstance(result.protocol_features["similarity_features"], list)
    assert isinstance(result.protocol_features["feature_norm"], float)


def test_gradients():
    """Check the gradients of the model parameters."""
    torch.manual_seed(7)
    core = MCPCore()
    namespaced = torch.randn(1, 4096)

    features = core.feature_extractor(namespaced)
    arbitration_scores = core.arbitration_head(features)
    similarity_features = core.similarity_head(features)
    mcp_tensor = F.normalize(features.squeeze(0), dim=-1)

    loss = mcp_tensor.sum() + arbitration_scores.sum() + similarity_features.sum()
    loss.backward()

    for name, param in core.named_parameters():
        assert param.grad is not None, f"Gradient for {name} is None"
        assert torch.all(torch.isfinite(param.grad)), f"Gradient for {name} is not finite"


def test_eval_mode():
    """Check the model in eval mode."""
    torch.manual_seed(7)
    core = MCPCore()
    core.eval()
    namespaced = torch.randn(1, 4096)

    with torch.no_grad():
        result = core(namespaced)

    assert isinstance(result, MCPResult)
    for module in core.modules():
        if isinstance(module, (torch.nn.Dropout, torch.nn.BatchNorm1d)):
            assert not module.training, f"{type(module).__name__} is not in eval mode"


def test_different_input_dim():
    """Check the model with a different input_dim."""
    torch.manual_seed(7)
    core = MCPCore(input_dim=2048)
    namespaced = torch.randn(1, 2048)

    result = core(namespaced)

    assert isinstance(result, MCPResult)
    assert result.processed_embedding.shape == (1, 128)
