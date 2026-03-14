"""
test_oidc_token.py - Tests for GitHub OIDC token verification.
"""
import pytest
from unittest.mock import patch, MagicMock
import jwt
import os

# We import the function to test.
# Note: The implementation in app/oidc_token.py might not have the new logic yet,
# so these tests are expected to fail or error out if run against the stub.
from app.oidc_token import verify_github_oidc_token

def test_verify_github_oidc_token_success():
    """Test successful token verification."""
    token = "valid_token"
    expected_claims = {
        "sub": "repo:org/repo:ref:refs/heads/main",
        "repository": "org/repo",
        "aud": "my-audience"
    }

    # We need to patch where the client is USED or DEFINED.
    # Since we plan to define jwks_client at module level in app.oidc_token, we patch it there.
    # But currently it doesn't exist. So we might need to patch jwt.PyJWKClient constructor if we instantiated it inside,
    # or rely on the fact that we will implement it.

    # Let's assume the implementation uses a global jwks_client.
    with patch("app.oidc_token.jwks_client") as mock_jwks_client,          patch("jwt.decode") as mock_jwt_decode,          patch.dict(os.environ, {"GITHUB_OIDC_AUDIENCE": "my-audience"}):

        mock_signing_key = MagicMock()
        mock_signing_key.key = "public_key"
        mock_jwks_client.get_signing_key_from_jwt.return_value = mock_signing_key
        mock_jwt_decode.return_value = expected_claims

        claims = verify_github_oidc_token(token)

        assert claims == expected_claims
        mock_jwks_client.get_signing_key_from_jwt.assert_called_once_with(token)
        mock_jwt_decode.assert_called_once_with(
            token,
            "public_key",
            algorithms=["RS256"],
            audience="my-audience",
            issuer="https://token.actions.githubusercontent.com",
        )

def test_verify_github_oidc_token_missing_audience():
    """Test verification fails when GITHUB_OIDC_AUDIENCE is not set."""
    # We patch jwks_client to avoid any potential side effects or errors if it was accessed
    with patch("app.oidc_token.jwks_client"),          patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="OIDC audience is not configured"):
            verify_github_oidc_token("token")

def test_verify_github_oidc_token_missing_repository_claim():
    """Test verification fails when repository claim is missing."""
    with patch("app.oidc_token.jwks_client") as mock_jwks_client,          patch("jwt.decode") as mock_jwt_decode,          patch.dict(os.environ, {"GITHUB_OIDC_AUDIENCE": "aud"}):

        mock_signing_key = MagicMock()
        mock_signing_key.key = "public_key"
        mock_jwks_client.get_signing_key_from_jwt.return_value = mock_signing_key
        mock_jwt_decode.return_value = {"sub": "foo"} # No repository

        with pytest.raises(ValueError, match="OIDC token missing repository claim"):
            verify_github_oidc_token("token")
