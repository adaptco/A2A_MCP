from __future__ import annotations

from orchestrator.multimodal_rag_workflow import (
    build_agentic_phase_stages,
    build_cicd_logic_tree,
    build_workflow_bundle,
    model_agentic_phase_loop,
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
    for node in reconstruction["nodes"]:
        for match in node["matches"]:
            assert -1.0 <= match["score"] <= 1.0


def test_agentic_phase_loop_contains_control_layer_handoffs():
    worldline = _sample_worldline()
    loop = model_agentic_phase_loop(worldline, top_k=3, min_similarity=0.0)

    assert loop["loop_id"] == "agentic-phase-loop.v1"
    assert len(loop["stages"]) == len(build_agentic_phase_stages())

    owners = [stage["owner_agent"] for stage in loop["stages"]]
    assert "ManagingAgent" in owners
    assert "OrchestrationAgent" in owners
    assert "CoderAgent" in owners

    token_object_stages = [stage for stage in loop["stages"] if stage["token_objects"]]
    assert token_object_stages
    token_object = token_object_stages[0]["token_objects"][0]
    assert "physics" in token_object
    assert "transform" in token_object
    assert token_object["object_id"].startswith("obj::")


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


def test_bundle_includes_agentic_phase_loop():
    worldline = _sample_worldline()
    bundle = build_workflow_bundle(worldline, top_k=2, min_similarity=0.0)

    phase_loop = bundle["agentic_phase_loop"]
    assert phase_loop["stages"]
    assert phase_loop["entry_phase"] == "IDLE"
