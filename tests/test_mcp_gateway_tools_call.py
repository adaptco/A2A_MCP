from fastapi.testclient import TestClient

from app.mcp_gateway import app


client = TestClient(app)


def test_tools_call_worldline_ingestion_success(monkeypatch):
    monkeypatch.setenv("OIDC_ENFORCE", "false")
    payload = {
        "tool_name": "ingest_worldline_block",
        "arguments": {
            "worldline_block": {
                "snapshot": {"repository": "adaptco/A2A_MCP"},
                "infrastructure_agent": {
                    "embedding_vector": [0.1],
                    "token_stream": [{"token": "hello", "token_id": "id1"}],
                    "artifact_clusters": {"cluster_0": ["artifact::hello"]},
                    "lora_attention_weights": {"cluster_0": 1.0},
                },
            },
            "authorization": "Bearer valid-token",
        },
    }
    response = client.post("/tools/call", json=payload, headers={"Authorization": "Bearer valid-token"})
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert "success" in body["result"]


def test_tools_call_unknown_tool_returns_404():
    response = client.post("/tools/call", json={"tool_name": "missing_tool", "arguments": {}})
    assert response.status_code == 404


def test_tools_call_rejects_invalid_oidc_token(monkeypatch):
    monkeypatch.setenv("OIDC_ENFORCE", "true")
    monkeypatch.setenv("OIDC_AUDIENCE", "a2a-test")
    payload = {
        "tool_name": "ingest_repository_data",
        "arguments": {
            "snapshot": {"repository": "adaptco/A2A_MCP"},
            "authorization": "Bearer invalid",
        },
    }
    response = client.post("/tools/call", json=payload, headers={"Authorization": "Bearer invalid"})
    assert response.status_code == 400
