from __future__ import annotations
import os
from typing import Any

from app.security.oidc import (
    OIDCAuthError,
    OIDCClaimError,
    enforce_avatar_ingest_allowlists,
    extract_bearer_token,
    get_request_correlation_id,
    validate_startup_oidc_requirements,
    verify_bearer_token,
)
from mcp.server.fastmcp import FastMCP

from app.mcp_tooling import (
    ingest_repository_data as protected_ingest_repository_data,
    verify_github_oidc_token as app_verify_github_oidc_token,
)

# Initialize FastMCP for secure knowledge ingestion
app_ingest = FastMCP("Knowledge Ingestion Service")

@app_ingest.tool()
def verify_github_oidc_token(token: str, request_id: str | None = None) -> dict[str, Any]:
    """Verify a GitHub OIDC token and return its claims."""
    correlation_id = request_id or get_request_correlation_id()
    return verify_bearer_token(token, request_id=correlation_id)


@app_ingest.tool()
def ingest_repository_data(snapshot: dict[str, Any], authorization: str, request_id: str | None = None) -> str:
    """Ingest a repository snapshot with OIDC provenance tracking."""
    correlation_id = request_id or get_request_correlation_id()

    try:
        token = extract_bearer_token(authorization)
        claims = verify_github_oidc_token(token, request_id=correlation_id)
    except OIDCAuthError:
        return f"error: unauthorized (request_id={correlation_id})"
    except OIDCClaimError:
        return f"error: forbidden (request_id={correlation_id})"

    repository = str(claims.get("repository", "")).strip()
    snapshot_repository = str(snapshot.get("repository", "")).strip()
    if snapshot_repository and snapshot_repository != repository:
        return f"error: repository claim mismatch (request_id={correlation_id})"

    route = str(snapshot.get("route", "")).strip().lower()
    if route == "avatar-ingest":
        try:
            enforce_avatar_ingest_allowlists(claims, request_id=correlation_id)
        except OIDCClaimError:
            return f"error: forbidden (request_id={correlation_id})"

    return f"success: ingested repository {repository} (request_id={correlation_id})"


@app_ingest.tool(name="ingest_worldline_block")
def ingest_worldline_block(worldline_block: dict[str, Any], authorization: str, request_id: str | None = None) -> str:
    """Ingest a multimodal worldline block for MCP orchestration."""
    correlation_id = request_id or get_request_correlation_id()

    try:
        token = extract_bearer_token(authorization)
        claims = verify_github_oidc_token(token, request_id=correlation_id)
    except OIDCAuthError:
        return f"error: unauthorized (request_id={correlation_id})"
    except OIDCClaimError:
        return f"error: forbidden (request_id={correlation_id})"

    snapshot = worldline_block.get("snapshot", {})
    repository = str(snapshot.get("repository", "")).strip()
    if repository and claims.get("repository") and claims["repository"] != repository:
        return f"error: repository claim mismatch (request_id={correlation_id})"

    infra = worldline_block.get("infrastructure", {})
    if not infra.get("token_stream"):
        return f"error: missing token_stream (request_id={correlation_id})"

    return (
        f"success: ingested worldline block for {repository or 'unknown-repository'} "
        f"with {len(infra.get('token_stream', []))} tokens (request_id={correlation_id})"
    )

if __name__ == "__main__":
    validate_startup_oidc_requirements()
    app_ingest.run()
