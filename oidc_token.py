"""
oidc_token – Stub for GitHub OIDC token verification.

Replace this stub with a real implementation (e.g. PyJWT + jwcrypto)
when deploying to production.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def verify_github_oidc_token(token: str) -> dict[str, Any]:
    """Validate a GitHub Actions OIDC JWT and return its claims.

    **Stub behaviour**: accepts any non-empty token and returns
    synthetic claims so that the rest of the pipeline can run
    in local / test environments.

    Parameters
    ----------
    token : str
        The raw JWT string from the ``Authorization: Bearer <token>`` header.

    Returns
    -------
    dict[str, Any]
        A dictionary of OIDC claims.

    Raises
    ------
    ValueError
        If *token* is empty or ``None``.
    """
    if not token:
        raise ValueError("OIDC token must not be empty")

    logger.warning(
        "oidc_token stub: accepting token without cryptographic verification"
    )

    return {
        "sub": "repo:stub-org/stub-repo:ref:refs/heads/main",
        "aud": "a2a-mcp",
        "iss": "https://token.actions.githubusercontent.com",
        "jti": "stub-jti-00000000",
        "repository": "stub-org/stub-repo",
        "actor": "stub-user",
    }
