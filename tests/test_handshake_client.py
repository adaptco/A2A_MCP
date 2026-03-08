from __future__ import annotations

import math
from pathlib import Path

from orchestrator.handshake_client import A2AHandshakeClient, HandshakeAgentProfile


def test_build_source_chunks_uses_allowed_corpus_and_payload_keys(tmp_path: Path):
    (tmp_path / "orchestrator").mkdir()
    (tmp_path / "agents").mkdir()
    (tmp_path / "schemas").mkdir()
    (tmp_path / "docs").mkdir()
    (tmp_path / "specs").mkdir()
    (tmp_path / "build").mkdir()
    (tmp_path / "orchestrator" / "__pycache__").mkdir()

    (tmp_path / "orchestrator" / "runtime_bridge.py").write_text(
        "def bridge():\n    return 'ok'\n",
        encoding="utf-8",
    )
    (tmp_path / "agents" / "coder.py").write_text(
        "class Coder:\n    pass\n",
        encoding="utf-8",
    )
    (tmp_path / "docs" / "README.md").write_text("# docs\n", encoding="utf-8")
    (tmp_path / "specs" / "judge.yaml").write_text("weights: []\n", encoding="utf-8")
    (tmp_path / "build" / "junk.py").write_text("ignored = True\n", encoding="utf-8")
    (tmp_path / "orchestrator" / "__pycache__" / "x.pyc").write_bytes(b"\x00\x01")

    with A2AHandshakeClient() as client:
        chunks = client.build_source_chunks(
            repo_root=tmp_path,
            grounding_tag="repo:sha:actor",
        )

    assert chunks
    paths = {chunk["path"] for chunk in chunks}
    assert "orchestrator/runtime_bridge.py" in paths
    assert "agents/coder.py" in paths
    assert "docs/README.md" in paths
    assert "specs/judge.yaml" in paths
    assert all("__pycache__" not in path for path in paths)
    assert all(not path.startswith("build/") for path in paths)
    for chunk in chunks:
        assert {"path", "sha", "chunk_index", "source_type", "grounding_tag"} <= set(
            chunk.keys()
        )


def test_embed_texts_falls_back_to_deterministic_vectors():
    with A2AHandshakeClient() as client:
        class _BrokenEmbedder:
            def encode(self, *_args, **_kwargs):
                raise RuntimeError("force fallback")

        client._embedder = _BrokenEmbedder()
        vectors = client.embed_texts(["alpha", "beta"])

    assert len(vectors) == 2
    assert len(vectors[0]) == 768
    norm = math.sqrt(sum(value * value for value in vectors[0]))
    assert abs(norm - 1.0) < 1e-6


def test_build_agent_spec_shapes_rbac_and_avatar_contract():
    with A2AHandshakeClient() as client:
        client.rbac.onboard_agent = lambda **_kwargs: {"onboarded": True}
        client.rbac.get_permissions = lambda **_kwargs: {
            "actions": ["run_pipeline"],
            "transitions": ["INIT->EMBEDDING"],
        }

        spec = client.build_agent_spec(
            HandshakeAgentProfile(
                agent_name="UnityTrainer",
                embedding_dim=768,
                avatar_key="engineer",
                rbac_role="pipeline_operator",
            )
        )

    metadata = spec["metadata"]
    assert metadata["avatar"]["avatar_id"]
    assert metadata["rbac"]["role"] == "pipeline_operator"
    assert metadata["rbac"]["actions"] == ["run_pipeline"]
    assert metadata["rag"]["collection"] == "a2a_worldline_rag_v1"
    assert metadata["lora"]["encoding"] == "weight_plus_unit_direction"


def test_build_lora_instruction_pairs_uses_verified_node_types():
    nodes = [
        {"text": "retry backoff", "metadata": {"type": "recovery_logic"}},
        {"text": "null guard", "metadata": {"type": "code_solution"}},
        {"text": "ignore me", "metadata": {"type": "research_doc"}},
    ]
    with A2AHandshakeClient() as client:
        pairs = client.build_lora_instruction_pairs(nodes)

    assert len(pairs) == 2
    assert pairs[0]["instruction"].startswith("SYSTEM:")
    assert pairs[0]["output"].startswith("ACTION:")


def test_build_handshake_payload_includes_snapshot_and_rag():
    with A2AHandshakeClient() as client:
        client.rbac.onboard_agent = lambda **_kwargs: {"onboarded": True}
        client.rbac.get_permissions = lambda **_kwargs: {}

        payload = client.build_handshake_payload(
            prompt="Deploy multimodal runtime workers",
            repository="adaptco/A2A_MCP",
            commit_sha="abc123",
            actor="qa_user",
            api_key="test-key",
            endpoint="https://example.invalid/mcp",
            agent_profiles=[
                HandshakeAgentProfile(agent_name="UnityTrainer", avatar_key="engineer"),
            ],
        )

    assert payload["snapshot"]["repository"] == "adaptco/A2A_MCP"
    assert payload["snapshot"]["commit_sha"] == "abc123"
    assert payload["snapshot"]["actor"] == "qa_user"
    assert payload["rag"]["collection"] == "a2a_worldline_rag_v1"
    assert payload["agent_specs"][0]["metadata"]["rbac"]["role"] == "pipeline_operator"
    assert payload["token_stream"]
