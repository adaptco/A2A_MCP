from __future__ import annotations

from unittest.mock import patch

from app.mcp_tooling import ToolAuthError, call_tool_by_name


def test_embedding_upsert_then_search(monkeypatch):
    monkeypatch.setenv("CHATGPT_APP_REQUIRE_AUTH_FOR_READ", "true")
    with patch(
        "app.mcp_tooling.verify_github_oauth_token",
        return_value={"actor": "octocat", "scopes": ["repo", "read:user"]},
    ):
        upsert = call_tool_by_name(
            tool_name="embedding_upsert",
            arguments={
                "namespace": "control-systems",
                "text": "deterministic worldline orchestration",
                "metadata": {"risk": "medium"},
            },
            authorization_header="Bearer oauth-token",
            request_id="trace-upsert-1",
        )
        assert isinstance(upsert, dict)
        assert upsert["ok"] is True
        assert upsert["record_id"]

        search = call_tool_by_name(
            tool_name="embedding_search",
            arguments={
                "namespace": "control-systems",
                "query": "worldline",
                "top_k": 3,
            },
            authorization_header="Bearer oauth-token",
            request_id="trace-search-1",
        )
        assert isinstance(search, dict)
        assert search["ok"] is True
        assert search["matches"]
        assert search["matches"][0]["record_id"] == upsert["record_id"]


def test_embedding_search_insufficient_scope_returns_structured_error():
    with patch(
        "app.mcp_tooling.verify_github_oauth_token",
        side_effect=ToolAuthError(
            code="INSUFFICIENT_SCOPE",
            message="missing oauth scopes: read:user",
            required_scopes=["read:user"],
        ),
    ):
        result = call_tool_by_name(
            tool_name="embedding_search",
            arguments={"query": "entropy"},
            authorization_header="Bearer weak-token",
            request_id="trace-scope-1",
        )
    assert isinstance(result, dict)
    assert result["ok"] is False
    assert result["error"]["code"] in {"AUTH_INVALID", "INSUFFICIENT_SCOPE"}


def test_embedding_workspace_data_contract(monkeypatch):
    monkeypatch.setenv("CHATGPT_APP_REQUIRE_AUTH_FOR_READ", "true")
    with patch(
        "app.mcp_tooling.verify_github_oauth_token",
        return_value={"actor": "octocat", "scopes": ["repo", "read:user"]},
    ):
        call_tool_by_name(
            tool_name="embedding_upsert",
            arguments={"namespace": "a2a", "text": "agent handoff receipt"},
            authorization_header="Bearer oauth-token",
            request_id="trace-upsert-2",
        )

        workspace = call_tool_by_name(
            tool_name="embedding_workspace_data",
            arguments={"namespace": "a2a", "query": "handoff"},
            authorization_header="Bearer oauth-token",
            request_id="trace-workspace-1",
        )
    assert isinstance(workspace, dict)
    assert workspace["ok"] is True
    assert isinstance(workspace["vectors"], list)
    assert isinstance(workspace["projections"], list)
    assert isinstance(workspace["summaries"], dict)


def test_orchestrate_command_adapter_maps_response():
    class DummyResponse:
        status_code = 200
        content = b'{"run_id":"run-123"}'
        text = '{"run_id":"run-123"}'

        @staticmethod
        def json():
            return {
                "run_id": "run-123",
                "status": "A2A Workflow Complete",
                "routing_decision": {"selected_agent": "Dot"},
                "trace_id": "trace-123",
            }

    with patch(
        "app.mcp_tooling.verify_github_oauth_token",
        return_value={"actor": "octocat", "scopes": ["repo", "read:user"]},
    ), patch("app.mcp_tooling.requests.post", return_value=DummyResponse()):
        result = call_tool_by_name(
            tool_name="orchestrate_command",
            arguments={
                "command": "!triage",
                "args": "stabilize gateway",
                "slack": {"channel_id": "C123"},
            },
            authorization_header="Bearer oauth-token",
            request_id="trace-orch-1",
        )
    assert isinstance(result, dict)
    assert result["ok"] is True
    assert result["run_id"] == "run-123"
    assert result["routing_decision"]["selected_agent"] == "Dot"
    assert result["trace_id"] == "trace-123"
