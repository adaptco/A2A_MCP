"""Module for GitHub OIDC token verification using PyJWT.

This module provides real verification using GitHub's JWKS endpoint.
"""

import os
import jwt
from jwt import PyJWKClient


# Global client instance to enable internal JWKS caching
GITHUB_JWKS_URL = "https://token.actions.githubusercontent.com/.well-known/jwks"
_jwks_client = PyJWKClient(GITHUB_JWKS_URL)


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
        If the token is invalid or verification fails.
    """
    if not token:
        raise ValueError("Empty OIDC token")

    issuer = "https://token.actions.githubusercontent.com"

    # The audience is usually configured in the OIDC trust relationship.
    # It should be provided via the GITHUB_OIDC_AUDIENCE environment variable.
    audience = os.getenv("GITHUB_OIDC_AUDIENCE")

    try:
        # Fetch JWKS and find the signing key (uses cache internally)
        signing_key = _jwks_client.get_signing_key_from_jwt(token)

        # Decode and verify the token
        # algorithms=["RS256"] is standard for GitHub OIDC
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=audience,
            issuer=issuer,
        )
        return claims
    except jwt.PyJWTError as e:
        raise ValueError(f"OIDC token verification failed: {str(e)}")
    except Exception as e:
        raise ValueError(f"Unexpected error during OIDC verification: {str(e)}")
