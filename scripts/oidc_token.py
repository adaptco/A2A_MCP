"""Stub module for GitHub OIDC token verification.

TODO: Replace with real verification using PyJWT + GitHub's JWKS endpoint
      (https://token.actions.githubusercontent.com/.well-known/jwks).
"""


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
    """
    # Stub implementation – always returns synthetic claims.
    return {
        "sub": "repo:stub-org/stub-repo:ref:refs/heads/main",
        "repository": "stub-org/stub-repo",
        "jti": f"stub-jti-{hash(token) % 10000:04d}",
    }
