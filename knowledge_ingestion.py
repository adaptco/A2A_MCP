from __future__ import annotations
import os
from typing import Any

import jwt
from fastmcp import FastMCP

app_ingest = FastMCP("knowledge-ingestion")


def verify_github_oidc_token(token: str) -> dict[str, Any]:
    if not token:
        raise ValueError("Invalid OIDC token")

    audience = os.getenv("GITHUB_OIDC_AUDIENCE")
    if not audience:
        raise ValueError("OIDC audience is not configured")

    jwks_client = jwt.PyJWKClient("https://token.actions.githubusercontent.com/.well-known/jwks")
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


@app_ingest.tool()
def ingest_repository_data(snapshot: dict[str, Any], authorization: str) -> str:
    if not authorization.startswith("Bearer "):
        return "error: missing bearer token"
    token = authorization.split(" ", 1)[1].strip()
    claims = verify_github_oidc_token(token)
    repository = str(claims.get("repository", "")).strip()

    snapshot_repository = str(snapshot.get("repository", "")).strip()
    if snapshot_repository and snapshot_repository != repository:
        return "error: repository claim mismatch"

    return f"success: ingested repository {repository}"
