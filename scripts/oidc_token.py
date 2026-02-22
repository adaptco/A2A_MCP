"""Module for GitHub OIDC token verification.

Implements real verification using PyJWT + GitHub's JWKS endpoint
(https://token.actions.githubusercontent.com/.well-known/jwks).
"""
import os
import jwt
from jwt import PyJWKClient

# Initialize JWKS client at module level to benefit from caching
jwks_client = PyJWKClient("https://token.actions.githubusercontent.com/.well-known/jwks")


def verify_github_oidc_token(token: str) -> dict:
    """Verify a GitHub Actions OIDC token and return its claims.

    Parameters
    ----------
    token : str
        The raw JWT bearer token from the Authorization header.

    Returns
    -------
    dict
        Decoded claims including 'sub', 'repository', and 'jti'.

    Raises
    ------
    ValueError
        If token is invalid, audience is not configured, or claims are missing.
    jwt.PyJWTError
        If JWT decoding fails.
    """
    if not token:
        raise ValueError("Invalid OIDC token")

    audience = os.getenv("GITHUB_OIDC_AUDIENCE")
    if not audience:
        raise ValueError("OIDC audience is not configured")

    signing_key = jwks_client.get_signing_key_from_jwt(token).key

    claims = jwt.decode(
        token,
        signing_key,
        algorithms=["RS256"],
        audience=audience,
        issuer="https://token.actions.githubusercontent.com",
    )

    repository = str(claims.get("repository", "")).strip()
    if not repository:
        raise ValueError("OIDC token missing repository claim")

    return claims
