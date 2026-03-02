import pytest

torch = pytest.importorskip("torch")

from a2a_mcp.mcp_core import MCPCore, MCPResult


def test_mcp_core_forward_shapes_and_hash():
    torch.manual_seed(7)
    core = MCPCore(hidden_dim=128, n_roles=32)
    namespaced = torch.randn(1, 4096)

    result = core(namespaced)

    assert isinstance(result, MCPResult)
    assert result.processed_embedding.shape == (1, 128)
    assert result.arbitration_scores.shape == (32,)
    assert result.protocol_features["feature_norm"] > 0.0
    assert len(result.execution_hash) == 64

    norm = float(torch.norm(result.processed_embedding, dim=-1).item())
    assert abs(norm - 1.0) < 1e-5


def test_protocol_similarity_returns_cosine_range():
    torch.manual_seed(11)
    core = MCPCore()
    emb = torch.randn(1, 4096)

    sim_same = core.compute_protocol_similarity(emb, emb.clone())
    assert -1.0 <= sim_same <= 1.0
    assert sim_same > 0.99
