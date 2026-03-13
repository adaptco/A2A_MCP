import os

import pytest

from app.security import oidc


def test_verify_token_relaxed_mode_returns_placeholder_claims(monkeypatch):
    monkeypatch.setenv("OIDC_ENFORCE", "false")
    claims = oidc.verify_github_oidc_token("valid-token")
    assert claims["actor"] == "unknown"


def test_verify_token_rejects_invalid_literal(monkeypatch):
    monkeypatch.setenv("OIDC_ENFORCE", "false")
    with pytest.raises(ValueError, match="Invalid OIDC token"):
        oidc.verify_github_oidc_token("invalid")


def test_verify_token_strict_mode_uses_decoder(monkeypatch):
    monkeypatch.setenv("OIDC_ENFORCE", "true")
    monkeypatch.setenv("OIDC_AUDIENCE", "a2a-test")

    captured = {}

    def fake_decode(token, settings):
        captured["token"] = token
        captured["issuer"] = settings.issuer
        return {"repository": "repo/name", "actor": "github-actions"}

    monkeypatch.setattr(oidc, "_decode_strict", fake_decode)
    claims = oidc.verify_github_oidc_token("header.payload.signature")

    assert claims["repository"] == "repo/name"
    assert captured["token"] == "header.payload.signature"
    assert captured["issuer"] == os.getenv("OIDC_ISSUER", "https://token.actions.githubusercontent.com")
