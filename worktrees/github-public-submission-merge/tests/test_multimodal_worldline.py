from orchestrator.multimodal_worldline import (
    build_worldline_block,
    cluster_artifacts,
    deterministic_embedding,
    lora_attention_weights,
)


def test_embedding_is_deterministic():
    v1 = deterministic_embedding("qube worldline")
    v2 = deterministic_embedding("qube worldline")
    assert v1 == v2
    assert len(v1) == 32


def test_cluster_weights_are_normalized():
    clusters = cluster_artifacts(["a", "b", "c", "d"], cluster_count=3)
    weights = lora_attention_weights(clusters)
    total = sum(weights.values())
    assert abs(total - 1.0) < 1e-9
    assert set(weights.keys()) == set(clusters.keys())


def test_worldline_block_contains_mcp_and_unity_payload():
    block = build_worldline_block(
        prompt="avatar prompt to multimodal worldline",
        repository="adaptco/A2A_MCP",
        commit_sha="abc123",
        actor="tester",
        cluster_count=4,
    )

    infra = block["infrastructure_agent"]
    assert infra["unity_object_class_name"].endswith("InfrastructureAgent")
    assert "UNITY_MCP_API_URL" in infra["unity_object_class_source"]
    assert len(infra["token_stream"]) > 0
    assert len(infra["embedding_vector"]) == 32

    tool_call = block["github_mcp_tool_call"]
    assert tool_call["tool_name"] == "ingest_worldline_block"
    assert tool_call["api_mapping"]["endpoint_env_var"] == "GITHUB_MCP_API_URL"
