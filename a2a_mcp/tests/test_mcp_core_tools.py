# import pytest

# from app.mcp_tooling import compute_protocol_similarity, run_mcp_core


# def test_run_mcp_core_with_small_dimension():
#     embedding = [0.01, 0.02, 0.03, 0.04]
#     result = run_mcp_core(embedding, input_dim=4, hidden_dim=4, n_roles=2)

#     assert "processed_embedding" in result
#     assert len(result["processed_embedding"]) == 4
#     assert len(result["arbitration_scores"]) == 2
#     assert isinstance(result["execution_hash"], str)


# def test_run_mcp_core_rejects_invalid_length():
#     with pytest.raises(ValueError, match="Expected embedding length"):
#         run_mcp_core([0.1, 0.2], input_dim=4, hidden_dim=4, n_roles=2)


# def test_compute_protocol_similarity_rejects_invalid_length():
#     with pytest.raises(ValueError, match="Expected embedding length"):
#         compute_protocol_similarity([0.1, 0.2], [0.3, 0.4], input_dim=8, hidden_dim=4, n_roles=2)
