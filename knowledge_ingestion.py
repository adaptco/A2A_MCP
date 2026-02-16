"""Compatibility shim for tests/imports expecting top-level knowledge_ingestion."""

from scripts.knowledge_ingestion import (
    app_ingest,
    ingest_repository_data,
    ingest_worldline_block,
    verify_github_oidc_token,
)

__all__ = [
    "app_ingest",
    "ingest_repository_data",
    "ingest_worldline_block",
    "verify_github_oidc_token",
]
