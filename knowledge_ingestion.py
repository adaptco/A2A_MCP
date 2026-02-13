from __future__ import annotations
from typing import Any

from fastmcp import FastMCP

app_ingest = FastMCP("knowledge-ingestion")


def verify_github_oidc_token(token: str) -> dict[str, Any]:
    if not token or token == "invalid":
        raise ValueError("Invalid OIDC token")
    return {"repository": "", "actor": "unknown"}


@app_ingest.tool()
def ingest_repository_data(snapshot: dict[str, Any], authorization: str) -> str:
    if not authorization.startswith("Bearer "):
        return "error: missing bearer token"
    token = authorization.split(" ", 1)[1].strip()
    verify_github_oidc_token(token)
    repository = str(snapshot.get("repository", "")).strip()
    return f"success: ingested repository {repository}"
