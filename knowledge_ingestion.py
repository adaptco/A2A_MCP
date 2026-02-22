from __future__ import annotations
from typing import Any

from fastmcp import FastMCP
from app.oidc_token import verify_github_oidc_token

app_ingest = FastMCP("knowledge-ingestion")


@app_ingest.tool()
def ingest_repository_data(snapshot: dict[str, Any], authorization: str) -> str:
    if not authorization.startswith("Bearer "):
        return "error: missing bearer token"
    token = authorization.split(" ", 1)[1].strip()

    try:
        claims = verify_github_oidc_token(token)
    except ValueError as e:
        return f"error: {str(e)}"

    repository = str(claims.get("repository", "")).strip()
    if not repository:
        return "error: OIDC token missing repository claim"

    snapshot_repository = str(snapshot.get("repository", "")).strip()
    if snapshot_repository and snapshot_repository != repository:
        return "error: repository claim mismatch"

    return f"success: ingested repository {repository}"
