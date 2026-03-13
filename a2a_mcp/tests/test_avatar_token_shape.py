from app import mcp_tooling
from app.mcp_tooling import ingest_avatar_token_stream
from app.security.avatar_token_shape import shape_avatar_token_stream


def test_shape_avatar_token_stream_is_deterministic() -> None:
    first = shape_avatar_token_stream(
        raw_tokens=[1.0, 2.0, 3.0],
        namespace="avatar::tenant-a",
        max_tokens=10,
        fingerprint_seed="repo/a",
    )
    second = shape_avatar_token_stream(
        raw_tokens=[1.0, 2.0, 3.0],
        namespace="avatar::tenant-a",
        max_tokens=10,
        fingerprint_seed="repo/a",
    )

    assert first.tokens == second.tokens
    assert first.execution_hash == second.execution_hash


def test_shape_avatar_token_stream_rejects_oversized_payload(monkeypatch) -> None:
    monkeypatch.setattr(
        mcp_tooling,
        "verify_github_oidc_token",
        lambda _token: {"repository": "adaptco/A2A_MCP"},
    )
    result = ingest_avatar_token_stream(
        payload={"tokens": [0.1, 0.2, 0.3], "namespace": "avatar::a", "max_tokens": 2},
        authorization="Bearer token",
    )

    assert result["ok"] is False
    assert result["error"]["code"] == "TOKEN_STREAM_TOO_LARGE"


def test_shape_avatar_token_stream_rejects_invalid_shape(monkeypatch) -> None:
    monkeypatch.setattr(
        mcp_tooling,
        "verify_github_oidc_token",
        lambda _token: {"repository": "adaptco/A2A_MCP"},
    )
    result = ingest_avatar_token_stream(
        payload={"tokens": [[1.0, 2.0]], "namespace": "avatar::a"},
        authorization="Bearer token",
    )

    assert result["ok"] is False
    assert result["error"]["code"] == "TOKEN_SHAPE_INVALID"
