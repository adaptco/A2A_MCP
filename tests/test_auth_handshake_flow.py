from __future__ import annotations

from datetime import datetime, timezone
import json

import pytest
from fastapi.testclient import TestClient

from app.multi_client_api import app, get_handshake_service, get_router
from app.services.auth_broker import A2AAuthBroker, AuthBrokerError, ClaimPolicyValidator
from app.services.handshake_service import A2AHandshakeService
from rbac.token_service import RBACJWTIssuer, TokenServiceError
from schemas.handshake import RbacClaimProposal


class _BrokerSuccessStub:
    def exchange(
        self,
        *,
        tenant_id: str,
        client_id: str,
        avatar_id: str,
        requested_scopes: list[str],
        requested_tools: list[str],
        ttl_seconds: int,
    ) -> dict[str, object]:
        proposal = RbacClaimProposal(
            tenant_id=tenant_id,
            client_id=client_id,
            avatar_id=avatar_id,
            roles=["pipeline_operator"],
            scopes=requested_scopes or ["mcp:handshake"],
            tools=requested_tools,
            ttl_seconds=ttl_seconds,
            reason="stub",
            source="test",
        )
        return {
            "claim_proposal": proposal,
            "rbac_access_token": "raw-rbac-token",
            "rbac_claims": {"sub": f"{client_id}:{avatar_id}"},
            "rbac_token_ref": "rbac://jwt/rbac-fp",
            "rbac_token_fingerprint": "rbac-fp",
            "gemini_access_token": "raw-gemini-token",
            "gemini_token_ref": "gemini://sa/gemini-fp",
            "gemini_token_fingerprint": "gemini-fp",
            "gemini_expires_in": 3600,
        }


class _BrokerFailureStub:
    def exchange(
        self,
        *,
        tenant_id: str,
        client_id: str,
        avatar_id: str,
        requested_scopes: list[str],
        requested_tools: list[str],
        ttl_seconds: int,
    ) -> dict[str, object]:
        raise AuthBrokerError("Claim proposal includes unsupported role")


def test_rbac_jwt_issue_and_expiry_enforced() -> None:
    issuer = RBACJWTIssuer(secret="unit-secret", issuer="unit-issuer", audience="unit-audience")
    token, claims = issuer.issue_access_token(
        {
            "sub": "client-x:avatar-y",
            "tenant_id": "tenant-x",
            "client_id": "client-x",
            "avatar_id": "avatar-y",
            "roles": ["pipeline_operator"],
            "scopes": ["mcp:handshake"],
            "tools": [],
        },
        ttl_seconds=300,
        now=int(datetime.now(timezone.utc).timestamp()),
    )
    decoded = issuer.verify_access_token(token)
    assert decoded["sub"] == "client-x:avatar-y"
    assert decoded["exp"] == claims["exp"]

    expired, _ = issuer.issue_access_token(
        {"sub": "client-x:avatar-y"},
        ttl_seconds=1,
        now=1,
    )
    with pytest.raises(TokenServiceError):
        issuer.verify_access_token(expired)


def test_claim_validator_rejects_invalid_role() -> None:
    validator = ClaimPolicyValidator()
    proposal = RbacClaimProposal(
        tenant_id="tenant-a",
        client_id="client-a",
        avatar_id="avatar-a",
        roles=["superuser"],
        scopes=["mcp:handshake"],
        tools=[],
        ttl_seconds=900,
    )
    with pytest.raises(AuthBrokerError):
        validator.validate(
            proposal,
            requested_scopes=["mcp:handshake"],
            requested_tools=[],
        )


def test_a2a_auth_broker_fails_closed_on_gemini_token_failure() -> None:
    class _Synth:
        def synthesize(
            self,
            *,
            tenant_id: str,
            client_id: str,
            avatar_id: str,
            requested_scopes: list[str],
            requested_tools: list[str],
            ttl_seconds: int,
        ) -> RbacClaimProposal:
            return RbacClaimProposal(
                tenant_id=tenant_id,
                client_id=client_id,
                avatar_id=avatar_id,
                roles=["pipeline_operator"],
                scopes=requested_scopes or ["mcp:handshake"],
                tools=requested_tools,
                ttl_seconds=ttl_seconds,
                source="test",
            )

    class _GeminiFail:
        def get_access_token(self, *, scopes: list[str]):
            raise AuthBrokerError("Gemini service-account token request failed")

    broker = A2AAuthBroker(
        synthesizer=_Synth(),
        validator=ClaimPolicyValidator(),
        rbac_issuer=RBACJWTIssuer(secret="s", issuer="i", audience="a"),
        gemini_provider=_GeminiFail(),
    )

    with pytest.raises(AuthBrokerError):
        broker.exchange(
            tenant_id="tenant-a",
            client_id="client-a",
            avatar_id="avatar-a",
            requested_scopes=["mcp:handshake"],
            requested_tools=["mcp.tool.echo"],
            ttl_seconds=900,
        )


def test_handshake_api_round_trip_stores_only_token_refs() -> None:
    get_router.cache_clear()
    get_handshake_service.cache_clear()

    service = A2AHandshakeService(broker=_BrokerSuccessStub())
    app.dependency_overrides[get_handshake_service] = lambda: service
    client = TestClient(app)
    try:
        init_response = client.post(
            "/a2a/handshake/init",
            json={
                "tenant_id": "tenant-a",
                "client_id": "client-a",
                "avatar_id": "avatar-a",
                "capabilities": ["mcp", "a2a", "rbac"],
                "metadata": {"source": "test"},
            },
        )
        assert init_response.status_code == 200
        handshake_id = init_response.json()["handshake_id"]

        exchange_response = client.post(
            "/a2a/handshake/exchange",
            params={"handshake_id": handshake_id},
            json={
                "requested_scopes": ["mcp:handshake", "world:model:read"],
                "requested_tools": ["mcp.tool.echo"],
                "ttl_seconds": 600,
            },
        )
        assert exchange_response.status_code == 200
        exchange_payload = exchange_response.json()
        assert exchange_payload["status"] == "exchanged"
        assert exchange_payload["rbac_token_ref"] == "rbac://jwt/rbac-fp"
        assert exchange_payload["gemini_token_ref"] == "gemini://sa/gemini-fp"
        assert "rbac_access_token" not in exchange_payload
        assert "gemini_access_token" not in exchange_payload

        runtime_tokens = service.get_runtime_tokens(handshake_id)
        assert runtime_tokens["rbac_access_token"] == "raw-rbac-token"
        assert runtime_tokens["gemini_access_token"] == "raw-gemini-token"
        assert "raw-rbac-token" not in json.dumps(exchange_payload)
        assert "raw-gemini-token" not in json.dumps(exchange_payload)

        finalize_response = client.post(
            "/a2a/handshake/finalize",
            params={"handshake_id": handshake_id},
            json={"metadata": {"finalized_by": "test"}},
        )
        assert finalize_response.status_code == 200
        assert finalize_response.json()["status"] == "finalized"
    finally:
        app.dependency_overrides.pop(get_handshake_service, None)
        get_handshake_service.cache_clear()
        get_router.cache_clear()


def test_handshake_api_fails_closed_for_invalid_claims() -> None:
    get_router.cache_clear()
    get_handshake_service.cache_clear()

    service = A2AHandshakeService(broker=_BrokerFailureStub())
    app.dependency_overrides[get_handshake_service] = lambda: service
    client = TestClient(app)
    try:
        init_response = client.post(
            "/a2a/handshake/init",
            json={
                "tenant_id": "tenant-b",
                "client_id": "client-b",
                "avatar_id": "avatar-b",
            },
        )
        assert init_response.status_code == 200
        handshake_id = init_response.json()["handshake_id"]

        exchange_response = client.post(
            "/a2a/handshake/exchange",
            params={"handshake_id": handshake_id},
            json={"requested_scopes": ["mcp:handshake"], "requested_tools": []},
        )
        assert exchange_response.status_code == 403
        assert "unsupported role" in exchange_response.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_handshake_service, None)
        get_handshake_service.cache_clear()
        get_router.cache_clear()
