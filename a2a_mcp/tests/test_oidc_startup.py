import pytest

from app.security.oidc import validate_startup_oidc_requirements


def test_prod_requires_mandatory_oidc(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("OIDC_ENFORCE", raising=False)
    monkeypatch.delenv("OIDC_ISSUER", raising=False)
    monkeypatch.delenv("OIDC_AUDIENCE", raising=False)
    monkeypatch.delenv("OIDC_JWKS_URL", raising=False)

    with pytest.raises(RuntimeError):
        validate_startup_oidc_requirements()


def test_non_prod_skips_mandatory_oidc(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "dev")
    validate_startup_oidc_requirements()
