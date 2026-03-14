"""Typed bridge contracts for exporting test receipts to a future qube-kernel."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Literal

from pydantic import BaseModel, Field


class TestArtifactDigest(BaseModel):
    """Hash metadata for a file included with the exported bridge receipt."""

    path: str
    sha256: str
    size_bytes: int = Field(ge=0)


class ChaosTestResult(BaseModel):
    """Normalized result for a single exported chaos or smoke test."""

    test_id: str
    outcome: Literal["passed", "failed", "skipped", "error", "xfailed", "xpassed"]
    duration_ms: float = Field(default=0.0, ge=0.0)
    message: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ChaosTestSummary(BaseModel):
    """Aggregate counts for a test receipt."""

    total: int = Field(ge=0)
    passed: int = Field(ge=0)
    failed: int = Field(ge=0)
    skipped: int = Field(ge=0)
    errors: int = Field(ge=0)
    xfailed: int = Field(default=0, ge=0)
    xpassed: int = Field(default=0, ge=0)


class AXISTestReceiptToken(BaseModel):
    """Structured AXIS token for an auditable signed receipt, not authentication."""

    schema_version: Literal["axis.receipt.token.v1"] = "axis.receipt.token.v1"
    token_id: str
    token_kind: Literal["signed_test_receipt"] = "signed_test_receipt"
    receipt_sha256: str
    signature: str
    signing_alg: Literal["hmac-sha256"] = "hmac-sha256"
    issued_at: str
    bridge_target: str = "qube-kernel"


class ChaosTestReceiptV1(BaseModel):
    """Signed bridge payload exported from A2A_MCP for downstream test consumers."""

    schema_version: Literal["chaos.test.receipt.v1"] = "chaos.test.receipt.v1"
    bridge_path: str = "a2a_mcp->qube_kernel"
    suite_name: str
    runner: str = "pytest"
    repository: str
    commit_sha: str
    status: Literal["passed", "failed"]
    summary: ChaosTestSummary
    tests: List[ChaosTestResult] = Field(default_factory=list)
    artifact_digests: List[TestArtifactDigest] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    axis_token: AXISTestReceiptToken
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
