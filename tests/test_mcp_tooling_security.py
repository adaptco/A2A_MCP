import pytest
from unittest.mock import patch
from app.mcp_tooling import call_tool_by_name


@pytest.mark.asyncio
async def test_call_tool_by_name_returns_error_for_unauthorized(monkeypatch):
    monkeypatch.setenv("OIDC_ENFORCE", "true")
    
    # Attempt to call a protected tool without authorization
    response = call_tool_by_name(
        tool_name="ingest_repository_data",
        arguments={"snapshot": {}},
        authorization_header=None,
        request_id="req-1"
    )
    
    assert response["ok"] is False
    assert response["error"]["code"] == "UNAUTHORIZED"
    assert response["error"]["request_id"] == "req-1"


@pytest.mark.asyncio
async def test_call_tool_by_name_returns_error_for_unknown_tool():
    with pytest.raises(KeyError):
        call_tool_by_name(
            tool_name="non_existent_tool",
            arguments={},
            request_id="req-2"
        )


@pytest.mark.asyncio
async def test_ingest_repository_data_enforces_repo_match(monkeypatch):
    monkeypatch.setenv("GITHUB_OIDC_AUDIENCE", "test-aud")
    
    mock_claims = {"repository": "allowed/repo", "actor": "test-actor"}
    
    with patch("app.mcp_tooling.verify_github_oidc_token", return_value=mock_claims):
        response = call_tool_by_name(
            tool_name="ingest_repository_data",
            arguments={"snapshot": {"repository": "malicious/repo"}},
            authorization_header="Bearer valid-token",
            request_id="req-3"
        )
        
        assert response["ok"] is False
        assert response["error"]["code"] == "REPOSITORY_CLAIM_MISMATCH"
