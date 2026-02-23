from __future__ import annotations

from fastapi.testclient import TestClient

import orchestrator.webhook as webhook


class _StubDBManager:
    def __init__(self) -> None:
        self.saved = []

    def save_artifact(self, artifact):
        self.saved.append(artifact)
        return artifact


def test_handshake_init_builds_full_state_payload(monkeypatch):
    stub_db = _StubDBManager()
    webhook.PLAN_STATE_MACHINES.clear()
    monkeypatch.setattr(webhook, "DBManager", lambda: stub_db)

    client = TestClient(webhook.app)
    response = client.post(
        "/handshake/init",
        json={
            "prompt": "Deploy WASD GameEngine workers with normalized token stream",
            "repository": "adaptco/A2A_MCP",
            "commit_sha": "abc123",
            "actor": "qa_user",
            "cluster_count": 3,
            "top_k": 2,
            "min_similarity": 0.0,
            "token_stream": [
                {"token": "WASD"},
                {"token": "GameEngine"},
                {"token": "WASD"},
            ],
            "agent_specs": [
                {
                    "agent_name": "UnityTrainer",
                    "model_id": "hf/high-fidelity",
                    "embedding_dim": 768,
                    "fidelity": "auto",
                    "role": "trainer",
                },
                {
                    "agent_name": "ThreeRuntime",
                    "model_id": "hf/compact-runtime",
                    "embedding_dim": 32,
                    "fidelity": "auto",
                    "role": "runtime",
                },
            ],
            "mcp": {
                "provider": "github-mcp",
                "tool_name": "ingest_worldline_block",
                "api_key": "super-secret-api-key",
                "endpoint": "https://example.invalid/mcp",
            },
            "runtime": {
                "wasm_shell": True,
                "engine": "WASD GameEngine",
                "unity_profile": "unity_lora_worker",
                "three_profile": "threejs_compact_worker",
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "handshake_initialized"

    state_payload = body["state_payload"]
    assert state_payload["handshake_id"].startswith("hs-")
    assert state_payload["plan_id"].startswith("plan-")
    assert state_payload["state_machine"]["state"] == "SCHEDULED"

    tokens = state_payload["normalized_token_stream"]
    assert [t["token"] for t in tokens] == ["wasd", "gameengine"]

    runtime = state_payload["runtime"]
    assert runtime["wasm_shell"]["enabled"] is True
    assert runtime["wasm_shell"]["engine"] == "WASD GameEngine"
    assert runtime["unity"]["purpose"] == "high_fidelity_lora_training"
    assert runtime["threejs"]["purpose"] == "low_dimensional_runtime_compaction"

    workers = state_payload["workers"]
    assert len(workers) == 2
    unity_worker = next(w for w in workers if w["agent_name"] == "UnityTrainer")
    three_worker = next(w for w in workers if w["agent_name"] == "ThreeRuntime")
    assert unity_worker["runtime_target"] == "unity_lora_worker"
    assert unity_worker["render_backend"] == "unity"
    assert three_worker["runtime_target"] == "threejs_compact_worker"
    assert three_worker["render_backend"] == "threejs"

    assert state_payload["mcp"]["provider"] == "github-mcp"
    assert len(state_payload["mcp"]["api_key_fingerprint"]) == 16

    assert len(state_payload["onboarded_artifacts"]) == 2
    assert len(stub_db.saved) == 5  # INIT + EMBEDDING + runtime.assignment.v1 bridge artifact
    bridge = state_payload["runtime_assignment_artifact"]
    assert bridge["type"] == "runtime.assignment.v1"
    assert bridge["content"]["schema_version"] == "runtime.assignment.v1"
    assert bridge["metadata"]["bridge_path"] == "orchestration_mcp->runtime_mcp"

    runtime_bridge_metadata = state_payload["runtime_bridge_metadata"]
    assert runtime_bridge_metadata["handshake_id"] == state_payload["handshake_id"]
    assert runtime_bridge_metadata["plan_id"] == state_payload["plan_id"]
    assert runtime_bridge_metadata["runtime_workers_ready"] == 2
    assert runtime_bridge_metadata["kernel_model_written"] is True

    worker_meta = next(w for w in workers if w["agent_name"] == "UnityTrainer")
    assert worker_meta["metadata"] == {}

    assert state_payload["workflow_actions"]
    assert state_payload["token_reconstruction"]["nodes"]


def test_handshake_requires_api_key(monkeypatch):
    webhook.PLAN_STATE_MACHINES.clear()
    monkeypatch.setattr(webhook, "DBManager", lambda: _StubDBManager())
    client = TestClient(webhook.app)

    response = client.post(
        "/handshake/init",
        json={
            "prompt": "missing key handshake",
            "repository": "adaptco/A2A_MCP",
            "commit_sha": "abc123",
            "mcp": {
                "provider": "github-mcp",
                "tool_name": "ingest_worldline_block",
            },
        },
    )
    assert response.status_code == 401
    assert "API key required" in response.json()["detail"]
