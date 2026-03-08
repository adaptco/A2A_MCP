from __future__ import annotations

from typing import Any

try:
    from fastmcp import FastMCP
except ModuleNotFoundError:
    from mcp.server.fastmcp import FastMCP

app_ingest = FastMCP("knowledge-ingestion")


def verify_github_oidc_token(token: str) -> dict[str, Any]:
    """
    Minimal verifier placeholder for tests.
    Real deployments should validate JWT signature/claims against GitHub OIDC.
    """
    if not token or token == "invalid":
        raise ValueError("Invalid OIDC token")
    return {"repository": "", "actor": "unknown"}


@app_ingest.tool(name="ingest_repository_data")
def ingest_repository_data(snapshot: dict[str, Any], authorization: str) -> str:
    if not authorization.startswith("Bearer "):
        return "error: missing bearer token"

    token = authorization.split(" ", 1)[1].strip()
    claims = verify_github_oidc_token(token)
    repository = str(snapshot.get("repository", "")).strip()

    if repository and claims.get("repository") and claims["repository"] != repository:
        return "error: repository claim mismatch"

    return f"success: ingested repository {repository}"


@app_ingest.tool(name="ingest_worldline_block")
def ingest_worldline_block(worldline_block: dict[str, Any], authorization: str) -> str:
    """Ingest a multimodal worldline block for MCP orchestration."""
    if not authorization.startswith("Bearer "):
        return "error: missing bearer token"

    token = authorization.split(" ", 1)[1].strip()
    claims = verify_github_oidc_token(token)

    snapshot = worldline_block.get("snapshot", {})
    repository = str(snapshot.get("repository", "")).strip()
    if repository and claims.get("repository") and claims["repository"] != repository:
        return "error: repository claim mismatch"

    infra = worldline_block.get("infrastructure_agent", {})
    if not isinstance(infra, dict):
        return "error: invalid infrastructure_agent payload"

    required = ["embedding_vector", "token_stream", "artifact_clusters", "lora_attention_weights"]
    missing = [field for field in required if field not in infra]
    if missing:
        return f"error: missing required fields: {', '.join(missing)}"

    return (
        "success: ingested worldline block "
        f"for {repository or 'unknown-repository'} "
        f"with {len(infra.get('token_stream', []))} tokens"
    )
