import asyncio
from types import SimpleNamespace

import pytest

from app.services.auth_middleware import require_auth


@require_auth
async def _protected_handler(*, request=None, context=None):
    return {
        "request_claims": getattr(getattr(request, "state", None), "auth_claims", None),
        "context_claims": (context or {}).get("auth_claims"),
    }


def test_require_auth_accepts_valid_signed_token(monkeypatch):
    signed_token = "header.payload.signature"
    claims = {"sub": "agent-123", "scope": "tools:read tools:write"}

    monkeypatch.setattr(
        "app.services.auth_middleware.verify_bearer_token",
        lambda token, request_id: claims if token == signed_token else None,
    )

    request = SimpleNamespace(headers={"Authorization": f"Bearer {signed_token}"}, state=SimpleNamespace())
    context = {}

    result = asyncio.run(_protected_handler(request=request, context=context))

    assert result["request_claims"] == claims
    assert result["context_claims"] == claims


def test_require_auth_rejects_malformed_token(monkeypatch):
    monkeypatch.setattr(
        "app.services.auth_middleware.verify_bearer_token",
        lambda token, request_id: {"sub": "ok"},
    )

    request = SimpleNamespace(headers={"Authorization": "Bearer"}, state=SimpleNamespace())

    with pytest.raises(PermissionError, match="Unauthorized access to agentic tools"):
        asyncio.run(_protected_handler(request=request))


def test_require_auth_rejects_random_long_string(monkeypatch):
    random_long_string = "x" * 256

    monkeypatch.setattr(
        "app.services.auth_middleware.verify_bearer_token",
        lambda token, request_id: (_ for _ in ()).throw(ValueError("invalid token")),
    )

    request = SimpleNamespace(
        headers={"Authorization": f"Bearer {random_long_string}"},
        state=SimpleNamespace(),
    )

    with pytest.raises(PermissionError, match="Unauthorized access to agentic tools"):
        asyncio.run(_protected_handler(request=request))


def test_require_auth_rejects_missing_header(monkeypatch):
    monkeypatch.setattr(
        "app.services.auth_middleware.verify_bearer_token",
        lambda token, request_id: {"sub": "ok"},
    )

    request = SimpleNamespace(headers={}, state=SimpleNamespace())

    with pytest.raises(PermissionError, match="Unauthorized access to agentic tools"):
        asyncio.run(_protected_handler(request=request))
