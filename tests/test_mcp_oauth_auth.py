from __future__ import annotations

from app.mcp_tooling import ToolAuthError, verify_github_oauth_token


class _MockResponse:
    def __init__(self, *, status_code: int, payload: dict, scopes: str = "") -> None:
        self.status_code = status_code
        self._payload = payload
        self.headers = {"X-OAuth-Scopes": scopes}
        self.content = b"{}"

    def json(self) -> dict:
        return self._payload


def test_verify_github_oauth_token_accepts_required_scopes(monkeypatch):
    def _fake_get(*_args, **_kwargs):
        return _MockResponse(
            status_code=200,
            payload={"login": "octocat", "id": 1},
            scopes="repo, read:user",
        )

    monkeypatch.setattr("app.mcp_tooling.requests.get", _fake_get)
    claims = verify_github_oauth_token("token", required_scopes=["repo"])
    assert claims["actor"] == "octocat"
    assert "repo" in claims["scopes"]


def test_verify_github_oauth_token_rejects_missing_scope(monkeypatch):
    def _fake_get(*_args, **_kwargs):
        return _MockResponse(
            status_code=200,
            payload={"login": "octocat", "id": 1},
            scopes="read:user",
        )

    monkeypatch.setattr("app.mcp_tooling.requests.get", _fake_get)
    try:
        verify_github_oauth_token("token", required_scopes=["repo"])
    except ToolAuthError as exc:
        assert exc.code == "INSUFFICIENT_SCOPE"
    else:
        raise AssertionError("Expected ToolAuthError")
