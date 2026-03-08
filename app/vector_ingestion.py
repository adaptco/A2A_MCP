"""Authenticated vector ingestion endpoint for repository snapshots."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Header, HTTPException

from app.mcp_tooling import ingest_repository_data, verify_github_oidc_token
from pipeline.vector_ingestion import VectorIngestionEngine, upsert_to_knowledge_store

app_ingest = FastAPI()
vector_engine = VectorIngestionEngine()


@app_ingest.post("/ingest")
async def ingest_repository(
    snapshot: dict[str, Any],
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    """Authenticated endpoint that indexes repository snapshots into Vector DB."""
    # 1. Validate A2A Proof (Handshake) and Repository Claims
    auth_result = ingest_repository_data(snapshot, authorization or "")
    if not auth_result.get("ok"):
        error = auth_result.get("error", {})
        status_code = 401 if error.get("code") == "AUTH_BEARER_MISSING" else 403
        raise HTTPException(status_code=status_code, detail=error)

    try:
        token = authorization.split(" ")[1]  # type: ignore
        claims = verify_github_oidc_token(token)

        # 2. Process & Embed (Phase 3 Integration)
        vector_nodes = await vector_engine.process_snapshot(snapshot, claims)

        # 3. Persistence
        result = await upsert_to_knowledge_store(vector_nodes)

        return {
            "status": "success",
            "ingestion_id": claims.get("jti", "batch_gen"),
            "indexed_count": result.get("count", 0),
            "provenance": auth_result["data"]["repository"],
            "execution_hash": auth_result["data"]["execution_hash"],
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(exc)}") from exc
