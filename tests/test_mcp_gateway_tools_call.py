from fastapi.testclient import TestClient
from unittest.mock import patch

from app.mcp_gateway import app


client = TestClient(app)


def test_tools_call_ingest_repository_data_success(monkeypatch):
    monkeypatch.setenv("OIDC_ENFORCE", "false")
    with patch(
        "app.mcp_tooling.verify_github_oidc_token",
        return_value={"repository": "adaptco/A2A_MCP", "actor": "github-actions"},
    ):
        payload = {
            "tool_name": "ingest_repository_data",
            "arguments": {
                "snapshot": {"repository": "adaptco/A2A_MCP"},
                "authorization": "Bearer valid-token",
            },
        }
        response = client.post("/tools/call", json=payload, headers={"Authorization": "Bearer valid-token"})
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["result"]["ok"] is True
    assert body["result"]["data"]["repository"] == "adaptco/A2A_MCP"


def test_tools_call_ingest_avatar_token_stream_success(monkeypatch):
    monkeypatch.setenv("OIDC_ENFORCE", "false")
    with patch(
        "app.mcp_tooling.verify_github_oidc_token",
        return_value={"repository": "adaptco/A2A_MCP", "actor": "github-actions"},
    ):
        payload = {
            "tool_name": "ingest_avatar_token_stream",
            "arguments": {
                "payload": {"tokens": [0.1, 0.2, 0.3], "max_tokens": 16},
                "authorization": "Bearer valid-token",
            },
        }
        response = client.post("/tools/call", json=payload, headers={"Authorization": "Bearer valid-token"})
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["result"]["ok"] is True
    assert body["result"]["data"]["token_count"] == 3


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
            "authorization": "Bearer valid-token",
        },
    }
    response = client.post("/tools/call", json=payload, headers={"Authorization": "Bearer invalid"})
    assert response.status_code == 400
