from __future__ import annotations

from orchestrator.multimodal_rag_workflow import (
    build_cicd_logic_tree,
    build_workflow_bundle,
    reconstruct_tokens_for_nodes,
    validate_bundle,
)
from orchestrator.multimodal_worldline import build_worldline_block


def _sample_worldline():
    return build_worldline_block(
        prompt="multimodal rag workflow for ci artifact orchestration",
        repository="adaptco/A2A_MCP",
        commit_sha="abc123",
        actor="tester",
        cluster_count=4,
    )


def test_logic_tree_contains_expected_nodes():
    worldline = _sample_worldline()
    nodes = build_cicd_logic_tree(worldline)

    assert [node.node_id for node in nodes] == [
        "N0_INGRESS",
        "N1_PLANNING",
        "N2_RAG_CONTEXT",
        "N3_EXECUTION",
        "N4_VALIDATION",
        "N5_RELEASE",
    ]
    assert all(node.allowed_actions for node in nodes)


def test_reconstruction_assigns_actions_per_node():
    worldline = _sample_worldline()
    reconstruction = reconstruct_tokens_for_nodes(worldline, top_k=3, min_similarity=0.0)

    assert reconstruction["vector_store_size"] > 0
    assert len(reconstruction["nodes"]) == 6
    assert all(node["selected_action"] for node in reconstruction["nodes"])
    assert all(node["gate_open"] for node in reconstruction["nodes"])


def test_reconstruction_handles_empty_token_stream():
    worldline = _sample_worldline()
    worldline["infrastructure_agent"]["token_stream"] = []
    worldline["infrastructure_agent"]["artifact_clusters"] = {}

    reconstruction = reconstruct_tokens_for_nodes(worldline, top_k=3, min_similarity=0.1)
    assert reconstruction["vector_store_size"] == 0
    assert any(not node["gate_open"] for node in reconstruction["nodes"])


def test_bundle_validation_fails_when_gates_closed():
    worldline = _sample_worldline()
    worldline["infrastructure_agent"]["token_stream"] = []
    worldline["infrastructure_agent"]["artifact_clusters"] = {}

    bundle = build_workflow_bundle(worldline)
    errors = validate_bundle(bundle)

    assert errors
    assert "gate is closed" in errors[0]
