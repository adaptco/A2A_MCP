from __future__ import annotations

import hashlib
import json

import jwt
import pytest
from fastapi import FastAPI, Header, HTTPException
from fastapi.testclient import TestClient

from avatars.avatar import AvatarProfile
from scripts.knowledge_ingestion import ingest_repository_data
from scripts.knowledge_ingestion import verify_github_oidc_token
from app.vector_ingestion import VectorIngestionEngine


@pytest.fixture
def sample_snapshot() -> dict[str, object]:
    return {
        "repository": "adaptco/A2A_MCP",
        "commit_sha": "abc123",
        "code_snippets": [
            {"file_path": "main.py", "content": "print('hello')", "language": "python"}
        ],
    }


def test_avatar_contract_requires_required_fields() -> None:
    with pytest.raises(ValueError, match="avatar_id is required"):
        AvatarProfile(avatar_id="", name="Valid Name")

    with pytest.raises(ValueError, match="name is required"):
        AvatarProfile(avatar_id="avatar-1", name="")


def test_ingestion_rejects_missing_bearer_token(sample_snapshot: dict[str, object]) -> None:
    assert ingest_repository_data(snapshot=sample_snapshot, authorization="Token abc") == "error: missing bearer token"


@pytest.mark.parametrize(
    "decode_error",
    [
        jwt.InvalidIssuerError("bad issuer"),
        jwt.InvalidAudienceError("bad audience"),
    ],
)
def test_verify_token_rejects_bad_issuer_or_audience(
    monkeypatch: pytest.MonkeyPatch,
    decode_error: Exception,
) -> None:
    monkeypatch.setenv("GITHUB_OIDC_AUDIENCE", "sigstore")

    class _MockJwkClient:
        def get_signing_key_from_jwt(self, _token: str):
            return type("SigningKey", (), {"key": "fake-key"})()

    monkeypatch.setattr("scripts.knowledge_ingestion.jwt.PyJWKClient", lambda _url: _MockJwkClient())

    def _raise(*_args, **_kwargs):
        raise decode_error

    monkeypatch.setattr("scripts.knowledge_ingestion.jwt.decode", _raise)

    with pytest.raises(type(decode_error)):
        verify_github_oidc_token("fake-token")


def test_ingestion_rejects_repository_claim_mismatch(sample_snapshot: dict[str, object], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "scripts.knowledge_ingestion.verify_github_oidc_token",
        lambda _token: {"repository": "adaptco/another-repo", "actor": "github-actions"},
    )

    response = ingest_repository_data(snapshot=sample_snapshot, authorization="Bearer fake-token")
    assert response == "error: repository claim mismatch"


@pytest.mark.asyncio
async def test_token_shaping_is_deterministic_for_identical_input_stream(sample_snapshot: dict[str, object]) -> None:
    engine = VectorIngestionEngine(embedding_dim=32)
    claims = {"actor": "github-actions"}

    first = await engine.process_snapshot(sample_snapshot, claims)
    second = await engine.process_snapshot(sample_snapshot, claims)

    assert first == second

    first_hash = hashlib.sha256(json.dumps(first, sort_keys=True).encode("utf-8")).hexdigest()
    second_hash = hashlib.sha256(json.dumps(second, sort_keys=True).encode("utf-8")).hexdigest()
    assert first_hash == second_hash


def test_tools_call_smoke_with_production_like_headers(
    sample_snapshot: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = FastAPI()

    @app.post("/tools/call")
    def call_tool(
        payload: dict,
        authorization: str = Header(default="", alias="Authorization"),
        x_github_repository: str = Header(default="", alias="X-GitHub-Repository"),
        x_github_actor: str = Header(default="", alias="X-GitHub-Actor"),
    ) -> dict[str, str]:
        if not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="missing bearer token")
        if not x_github_repository or not x_github_actor:
            raise HTTPException(status_code=401, detail="missing required provenance headers")

        result = ingest_repository_data(snapshot=payload.get("snapshot", {}), authorization=authorization)
        if result.startswith("error"):
            raise HTTPException(status_code=403, detail=result)
        return {"status": result}

    monkeypatch.setattr(
        "scripts.knowledge_ingestion.verify_github_oidc_token",
        lambda _token: {"repository": "adaptco/A2A_MCP", "actor": "github-actions"},
    )

    client = TestClient(app)
    response = client.post(
        "/tools/call",
        json={"snapshot": sample_snapshot},
        headers={
            "Authorization": "Bearer valid-token",
            "X-GitHub-Repository": "adaptco/A2A_MCP",
            "X-GitHub-Actor": "github-actions",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"].startswith("success")
