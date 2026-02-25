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
    monkeypatch.setenv("A2A_ORCHESTRATION_MODEL", "codestral-latest")
    monkeypatch.setenv("A2A_ORCHESTRATION_EMBEDDING_LANGUAGE", "code")
    monkeypatch.setenv("LLM_API_KEY", "local-llm-key")
    monkeypatch.setenv("RBAC_SECRET", "local-rbac-secret")
    monkeypatch.setenv("A2A_MCP_API_TOKEN", "mcp-token-value")

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
                    "metadata": {
                        "avatar": {"avatar_id": "avatar_unity_trainer", "style": "engineer"},
                        "rbac": {"agent_id": "agent-unitytrainer", "role": "pipeline_operator"},
                    },
                },
                {
                    "agent_name": "ThreeRuntime",
                    "model_id": "hf/compact-runtime",
                    "embedding_dim": 32,
                    "fidelity": "auto",
                    "role": "runtime",
                    "metadata": {
                        "avatar": {"avatar_id": "avatar_three_runtime", "style": "driver"},
                        "rbac": {"agent_id": "agent-threeruntime", "role": "observer"},
                    },
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
    assert state_payload["rag"]["collection"] == "a2a_worldline_rag_v1"
    assert state_payload["snapshot"]["repository"] == "adaptco/A2A_MCP"
    assert state_payload["snapshot"]["commit_sha"] == "abc123"
    assert state_payload["snapshot"]["actor"] == "qa_user"

    workers = state_payload["workers"]
    assert len(workers) == 2
    unity_worker = next(w for w in workers if w["agent_name"] == "UnityTrainer")
    three_worker = next(w for w in workers if w["agent_name"] == "ThreeRuntime")
    assert unity_worker["runtime_target"] == "unity_lora_worker"
    assert unity_worker["render_backend"] == "unity"
    assert three_worker["runtime_target"] == "threejs_compact_worker"
    assert three_worker["render_backend"] == "threejs"
    assert unity_worker["avatar"]["avatar_id"] == "avatar_unity_trainer"
    assert unity_worker["rbac"]["role"] == "pipeline_operator"
    assert three_worker["avatar"]["style"] == "driver"
    assert three_worker["rbac"]["role"] == "observer"

    assert state_payload["mcp"]["provider"] == "github-mcp"
    assert len(state_payload["mcp"]["api_key_fingerprint"]) == 16

    assert len(state_payload["onboarded_artifacts"]) == 2
    assert len(stub_db.saved) == 5  # INIT + EMBEDDING + runtime.assignment.v1 bridge artifact
    unity_init = next(
        artifact
        for artifact in stub_db.saved
        if getattr(artifact, "agent_name", "") == "UnityTrainer"
        and getattr(getattr(artifact, "state", None), "value", "") == "INIT"
    )
    assert unity_init.lora_config is not None
    assert unity_init.lora_config.direction_vectors

    bridge = state_payload["runtime_assignment_artifact"]
    assert bridge["type"] == "runtime.assignment.v1"
    assert bridge["content"]["schema_version"] == "runtime.assignment.v1"
    assert bridge["metadata"]["bridge_path"] == "orchestration_mcp->runtime_mcp"

    runtime_bridge_metadata = state_payload["runtime_bridge_metadata"]
    assert runtime_bridge_metadata["handshake_id"] == state_payload["handshake_id"]
    assert runtime_bridge_metadata["plan_id"] == state_payload["plan_id"]
    assert runtime_bridge_metadata["runtime_workers_ready"] == 2
    assert runtime_bridge_metadata["kernel_model_written"] is True

    dmn_globals = state_payload["dmn_global_variables"]
    assert dmn_globals
    dmn_names = [item["name"] for item in dmn_globals]
    assert dmn_names == sorted(dmn_names)
    assert any(
        item["name"] == "A2A_RUNTIME_ENGINE"
        and item["value"] == "WASD GameEngine"
        and item["dmn_key"] == "runtime.engine"
        for item in dmn_globals
    )
    assert any(
        item["name"] == "A2A_MCP_PROVIDER"
        and item["value"] == "github-mcp"
        and item["dmn_key"] == "mcp.provider"
        for item in dmn_globals
    )
    assert any(
        item["name"] == "A2A_ORCHESTRATION_MODEL"
        and item["value"] == "codestral-latest"
        and item["dmn_key"] == "runtime.orchestration.model"
        for item in dmn_globals
    )
    assert any(
        item["name"] == "A2A_ORCHESTRATION_EMBEDDING_LANGUAGE"
        and item["value"] == "code"
        and item["dmn_key"] == "runtime.orchestration.embedding_language"
        for item in dmn_globals
    )
    assert any(
        item["name"] == "LLM_API_KEY"
        and item["value"].startswith("sha256:")
        and item["value"] != "local-llm-key"
        for item in dmn_globals
    )
    assert any(
        item["name"] == "RBAC_SECRET"
        and item["value"].startswith("sha256:")
        and item["value"] != "local-rbac-secret"
        for item in dmn_globals
    )
    assert any(
        item["name"] == "A2A_MCP_API_TOKEN"
        and item["value"].startswith("sha256:")
        and item["value"] != "mcp-token-value"
        for item in dmn_globals
    )
    xml_payload = state_payload["dmn_global_variables_xml"]
    assert xml_payload.startswith("<dmnGlobalVariables")
    assert "A2A_RUNTIME_ENGINE" in xml_payload
    assert "dmnKey=\"runtime.engine\"" in xml_payload

    worker_meta = next(w for w in workers if w["agent_name"] == "UnityTrainer")
    assert worker_meta["metadata"] == {}
    worldline = state_payload["worldline_block"]
    assert worldline["infrastructure_agent"]["lora_weight_directions"]

    assert state_payload["workflow_actions"]
    assert state_payload["token_reconstruction"]["nodes"]
    phase_loop = state_payload["agentic_phase_loop"]
    assert phase_loop["stages"]
    assert phase_loop["entry_phase"] == "IDLE"
    assert any(stage["owner_agent"] == "ManagingAgent" for stage in phase_loop["stages"])
    assert any(stage["owner_agent"] == "CoderAgent" for stage in phase_loop["stages"])


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


def test_handshake_orchestration_profile_fallbacks(monkeypatch):
    webhook.PLAN_STATE_MACHINES.clear()
    monkeypatch.setattr(webhook, "DBManager", lambda: _StubDBManager())
    monkeypatch.delenv("A2A_ORCHESTRATION_MODEL", raising=False)
    monkeypatch.delenv("A2A_ORCHESTRATION_EMBEDDING_LANGUAGE", raising=False)
    monkeypatch.setenv("LLM_MODEL", "fallback-llm-model")

    client = TestClient(webhook.app)
    response = client.post(
        "/handshake/init",
        json={
            "prompt": "fallback profile check",
            "repository": "adaptco/A2A_MCP",
            "commit_sha": "abc123",
            "mcp": {
                "provider": "github-mcp",
                "tool_name": "ingest_worldline_block",
                "api_key": "super-secret-api-key",
            },
        },
    )

    assert response.status_code == 200
    dmn_globals = response.json()["state_payload"]["dmn_global_variables"]
    assert any(
        item["name"] == "A2A_ORCHESTRATION_MODEL"
        and item["value"] == "fallback-llm-model"
        and item["dmn_key"] == "runtime.orchestration.model"
        for item in dmn_globals
    )
    assert any(
        item["name"] == "A2A_ORCHESTRATION_EMBEDDING_LANGUAGE"
        and item["value"] == "code"
        and item["dmn_key"] == "runtime.orchestration.embedding_language"
        for item in dmn_globals
    )
