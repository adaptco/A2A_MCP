from __future__ import annotations

from fastmcp import FastMCP

app_ingest = FastMCP("knowledge-ingestion")


def verify_github_oidc_token(token: str):
    """Placeholder verifier for GitHub OIDC tokens."""
    raise NotImplementedError("OIDC verification is not implemented in local test mode.")


@app_ingest.tool()
async def ingest_repository_data(snapshot: dict, authorization: str) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        return "error: missing bearer token"

    token = authorization.split(" ", 1)[1]
    claims = verify_github_oidc_token(token)
    repository = claims.get("repository", "unknown") if isinstance(claims, dict) else "unknown"
    return f"success: ingested snapshot for {repository}"
