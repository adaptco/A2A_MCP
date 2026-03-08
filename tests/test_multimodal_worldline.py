from orchestrator.multimodal_worldline import (
    _pascal_case,
    build_worldline_block,
    cluster_artifacts,
    deterministic_embedding,
    lora_attention_weights,
    token_to_id,
    tokenize_prompt,
)


def test_embedding_is_deterministic():
    v1 = deterministic_embedding("qube worldline")
    v2 = deterministic_embedding("qube worldline")
    assert v1 == v2
    assert len(v1) == 32


def test_embedding_edge_cases():
    # Empty string
    v_empty = deterministic_embedding("")
    assert len(v_empty) == 32

    # Different dimensions
    v_1 = deterministic_embedding("test", dimensions=1)
    assert len(v_1) == 1

    # Large dimensions (greater than sha256 digest length 32)
    v_100 = deterministic_embedding("test", dimensions=100)
    assert len(v_100) == 100
    # Values should still be in [-1, 1]
    for val in v_100:
        assert -1.0 <= val <= 1.0


def test_tokenize_prompt_edge_cases():
    assert tokenize_prompt("") == []
    assert tokenize_prompt("!@#$%^&*()") == []
    assert tokenize_prompt("Mixed CASE words 123") == ["mixed", "case", "words", "123"]
    assert tokenize_prompt("hello_world 42") == ["hello_world", "42"]


def test_token_to_id_edge_cases():
    tid1 = token_to_id("token", 0)
    tid2 = token_to_id("token", 1)
    assert tid1 != tid2
    assert len(tid1) == 16
    assert token_to_id("", 0) != ""


def test_cluster_artifacts_edge_cases():
    # Empty artifacts
    assert cluster_artifacts([], cluster_count=4) == {
        "cluster_0": [], "cluster_1": [], "cluster_2": [], "cluster_3": []
    }

    # cluster_count = 1
    c1 = cluster_artifacts(["a", "b", "c"], cluster_count=1)
    assert len(c1) == 1
    assert len(c1["cluster_0"]) == 3

    # cluster_count <= 0 (handled by max(1, count))
    c0 = cluster_artifacts(["a", "b"], cluster_count=0)
    assert len(c0) == 1
    assert "cluster_0" in c0

    cn = cluster_artifacts(["a", "b"], cluster_count=-5)
    assert len(cn) == 1

    # Generator input
    gen = (a for a in ["a", "b", "c"])
    cg = cluster_artifacts(gen, cluster_count=2)
    assert len(cg) == 2
    assert sum(len(v) for v in cg.values()) == 3


def test_cluster_artifacts_distribution():
    # Test that artifacts are distributed across clusters
    artifacts = [f"art_{i}" for i in range(100)]
    clusters = cluster_artifacts(artifacts, cluster_count=4)

    # Check that not all artifacts are in the same cluster
    for name, items in clusters.items():
        assert len(items) < 100

    # Check that they are all there
    assert sum(len(items) for items in clusters.values()) == 100


def test_cluster_weights_are_normalized():
    clusters = cluster_artifacts(["a", "b", "c", "d"], cluster_count=3)
    weights = lora_attention_weights(clusters)
    total = sum(weights.values())
    assert abs(total - 1.0) < 1e-9
    assert set(weights.keys()) == set(clusters.keys())


def test_lora_attention_weights_edge_cases():
    # No items in any cluster
    clusters = {"c0": [], "c1": []}
    weights = lora_attention_weights(clusters)
    assert weights == {"c0": 0.5, "c1": 0.5}

    # Empty clusters dict
    assert lora_attention_weights({}) == {}

    # Some clusters empty, some not
    clusters = {"c0": ["a", "b"], "c1": []}
    weights = lora_attention_weights(clusters)
    assert weights["c0"] == 1.0
    assert weights["c1"] == 0.0


def test_pascal_case_edge_cases():
    assert _pascal_case("") == "QubeAgent"
    assert _pascal_case("hello_world") == "HelloWorld"
    # Note: capitalize() makes the rest lowercase
    assert _pascal_case("alreadyPascal") == "Alreadypascal"
    assert _pascal_case("Multiple   spaces") == "MultipleSpaces"
    assert _pascal_case("123numbers") == "123numbers"
    assert _pascal_case("!!!") == "QubeAgent"


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
    assert block["snapshot"]["repository"] == "adaptco/A2A_MCP"

    tool_call = block["github_mcp_tool_call"]
    assert tool_call["tool_name"] == "ingest_worldline_block"
    assert tool_call["api_mapping"]["endpoint_env_var"] == "GITHUB_MCP_API_URL"


def test_build_worldline_block_empty_prompt():
    block = build_worldline_block(
        prompt="",
        repository="repo",
        commit_sha="sha",
    )
    assert block["infrastructure_agent"]["unity_object_class_name"] == "QubeAgentInfrastructureAgent"
    assert block["infrastructure_agent"]["token_stream"] == []
    # Should have a default artifact if no tokens
    clusters = block["infrastructure_agent"]["artifact_clusters"]
    total_artifacts = sum(len(c) for c in clusters.values())
    assert total_artifacts == 1
    assert any("artifact::default" in c for c in clusters.values())
