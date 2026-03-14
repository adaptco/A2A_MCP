"""Bridge helpers for exporting signed test receipts to a future qube-kernel."""

from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from orchestrator.capsule_store import canonical_json
from schemas.agent_artifacts import MCPArtifact
from schemas.qube_kernel_bridge import (
    AXISTestReceiptToken,
    ChaosTestReceiptV1,
    ChaosTestResult,
    ChaosTestSummary,
    TestArtifactDigest,
)

_PASSING_OUTCOMES = {"passed", "skipped", "xfailed"}
_FAILING_OUTCOMES = {"failed", "error", "xpassed"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _coerce_signing_secret(signing_secret: str | bytes) -> bytes:
    if isinstance(signing_secret, bytes):
        secret = signing_secret
    else:
        secret = signing_secret.encode("utf-8")
    if not secret:
        raise ValueError("signing_secret must be non-empty")
    return secret


def _coerce_test_results(
    test_results: Sequence[ChaosTestResult | Mapping[str, Any]],
) -> list[ChaosTestResult]:
    normalized = [
        result
        if isinstance(result, ChaosTestResult)
        else ChaosTestResult.model_validate(result)
        for result in test_results
    ]
    if not normalized:
        raise ValueError("test_results must include at least one result")
    return normalized


def build_test_artifact_digests(paths: Iterable[str | Path]) -> list[TestArtifactDigest]:
    """Hash supporting files so a downstream bridge consumer can verify them."""
    digests: list[TestArtifactDigest] = []
    for raw_path in paths:
        path = Path(raw_path)
        if not path.exists() or not path.is_file():
            raise ValueError(f"artifact path does not exist or is not a file: {path}")
        payload = path.read_bytes()
        digests.append(
            TestArtifactDigest(
                path=str(path),
                sha256=hashlib.sha256(payload).hexdigest(),
                size_bytes=len(payload),
            )
        )
    return digests


def build_test_summary(
    test_results: Sequence[ChaosTestResult | Mapping[str, Any]],
) -> ChaosTestSummary:
    """Aggregate normalized test result counts for the exported receipt."""
    results = _coerce_test_results(test_results)
    counts = {
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "errors": 0,
        "xfailed": 0,
        "xpassed": 0,
    }
    for result in results:
        if result.outcome == "error":
            counts["errors"] += 1
        else:
            counts[result.outcome] += 1

    return ChaosTestSummary(
        total=len(results),
        passed=counts["passed"],
        failed=counts["failed"],
        skipped=counts["skipped"],
        errors=counts["errors"],
        xfailed=counts["xfailed"],
        xpassed=counts["xpassed"],
    )


def _build_axis_token(
    receipt_payload: Mapping[str, Any],
    *,
    signing_secret: str | bytes,
    issued_at: str,
    bridge_target: str,
) -> AXISTestReceiptToken:
    receipt_sha256 = hashlib.sha256(
        canonical_json(dict(receipt_payload)).encode("utf-8")
    ).hexdigest()
    signature = hmac.new(
        _coerce_signing_secret(signing_secret),
        receipt_sha256.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return AXISTestReceiptToken(
        token_id=f"axis-{receipt_sha256[:16]}",
        receipt_sha256=receipt_sha256,
        signature=signature,
        issued_at=issued_at,
        bridge_target=bridge_target,
    )


def build_qube_kernel_test_receipt(
    *,
    suite_name: str,
    repository: str,
    commit_sha: str,
    test_results: Sequence[ChaosTestResult | Mapping[str, Any]],
    signing_secret: str | bytes,
    artifact_paths: Iterable[str | Path] = (),
    runner: str = "pytest",
    generated_at: str | None = None,
    bridge_path: str = "a2a_mcp->qube_kernel",
    bridge_target: str = "qube-kernel",
    metadata: Mapping[str, Any] | None = None,
) -> ChaosTestReceiptV1:
    """Build a signed receipt that can be consumed by a future qube-kernel bridge."""
    if not suite_name.strip():
        raise ValueError("suite_name must be non-empty")
    if not repository.strip():
        raise ValueError("repository must be non-empty")
    if not commit_sha.strip():
        raise ValueError("commit_sha must be non-empty")

    results = _coerce_test_results(test_results)
    summary = build_test_summary(results)
    artifact_digests = build_test_artifact_digests(artifact_paths)
    receipt_time = generated_at or _utc_now()
    status = (
        "failed"
        if summary.failed or summary.errors or summary.xpassed or any(
            result.outcome in _FAILING_OUTCOMES for result in results
        )
        else "passed"
    )
    receipt_metadata = dict(metadata or {})
    receipt_metadata.setdefault("bridge_target", bridge_target)
    receipt_metadata.setdefault("suite_kind", "chaos")

    unsigned_receipt = {
        "schema_version": "chaos.test.receipt.v1",
        "bridge_path": bridge_path,
        "suite_name": suite_name,
        "runner": runner,
        "repository": repository,
        "commit_sha": commit_sha,
        "status": status,
        "summary": summary.model_dump(mode="json"),
        "tests": [result.model_dump(mode="json") for result in results],
        "artifact_digests": [
            digest.model_dump(mode="json") for digest in artifact_digests
        ],
        "metadata": receipt_metadata,
        "generated_at": receipt_time,
    }
    axis_token = _build_axis_token(
        unsigned_receipt,
        signing_secret=signing_secret,
        issued_at=receipt_time,
        bridge_target=bridge_target,
    )

    return ChaosTestReceiptV1(
        suite_name=suite_name,
        runner=runner,
        repository=repository,
        commit_sha=commit_sha,
        status=status,
        summary=summary,
        tests=results,
        artifact_digests=artifact_digests,
        metadata=receipt_metadata,
        axis_token=axis_token,
        generated_at=receipt_time,
        bridge_path=bridge_path,
    )


def verify_axis_token(
    receipt: ChaosTestReceiptV1 | Mapping[str, Any],
    *,
    signing_secret: str | bytes,
) -> bool:
    """Verify that a receipt's AXIS token still matches its unsigned payload."""
    model = (
        receipt
        if isinstance(receipt, ChaosTestReceiptV1)
        else ChaosTestReceiptV1.model_validate(receipt)
    )
    unsigned_receipt = model.model_dump(mode="json", exclude={"axis_token"})
    expected_sha256 = hashlib.sha256(
        canonical_json(unsigned_receipt).encode("utf-8")
    ).hexdigest()
    if not hmac.compare_digest(expected_sha256, model.axis_token.receipt_sha256):
        return False

    expected_signature = hmac.new(
        _coerce_signing_secret(signing_secret),
        expected_sha256.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected_signature, model.axis_token.signature)


def build_qube_kernel_test_artifact(
    *,
    suite_name: str,
    repository: str,
    commit_sha: str,
    test_results: Sequence[ChaosTestResult | Mapping[str, Any]],
    signing_secret: str | bytes,
    artifact_paths: Iterable[str | Path] = (),
    runner: str = "pytest",
    generated_at: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> MCPArtifact:
    """Wrap a signed test receipt in the repo's standard MCPArtifact envelope."""
    receipt = build_qube_kernel_test_receipt(
        suite_name=suite_name,
        repository=repository,
        commit_sha=commit_sha,
        test_results=test_results,
        signing_secret=signing_secret,
        artifact_paths=artifact_paths,
        runner=runner,
        generated_at=generated_at,
        metadata=metadata,
    )
    return MCPArtifact(
        artifact_id=receipt.axis_token.token_id,
        agent_name="QubeKernelBridge",
        version="1.0.0",
        type=receipt.schema_version,
        content=receipt.model_dump(mode="json"),
        timestamp=receipt.generated_at,
        metadata={
            "bridge_path": receipt.bridge_path,
            "suite_name": receipt.suite_name,
            "status": receipt.status,
            "repository": receipt.repository,
            "commit_sha": receipt.commit_sha,
            "axis_token_id": receipt.axis_token.token_id,
        },
    )


def export_qube_kernel_test_artifact(
    artifact: MCPArtifact | Mapping[str, Any],
    output_path: str | Path,
) -> dict[str, Any]:
    """Write the canonical artifact payload to disk for a downstream repo handoff."""
    model = artifact if isinstance(artifact, MCPArtifact) else MCPArtifact.model_validate(artifact)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = canonical_json(model.model_dump(mode="json"))
    path.write_text(payload, encoding="utf-8")
    return {
        "path": str(path),
        "sha256": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        "bytes": len(payload.encode("utf-8")),
    }


__all__ = [
    "build_qube_kernel_test_artifact",
    "build_qube_kernel_test_receipt",
    "build_test_artifact_digests",
    "build_test_summary",
    "export_qube_kernel_test_artifact",
    "verify_axis_token",
]
