from __future__ import annotations

import hashlib
import json
from pathlib import Path

from orchestrator.qube_kernel_bridge import (
    build_qube_kernel_test_artifact,
    export_qube_kernel_test_artifact,
    verify_axis_token,
)
from schemas.qube_kernel_bridge import ChaosTestReceiptV1


def test_build_qube_kernel_test_artifact_is_deterministic_and_signed(
    tmp_path: Path,
) -> None:
    log_path = tmp_path / "chaos.log"
    log_path.write_text("bridge-first chaos smoke\n", encoding="utf-8")
    test_results = [
        {
            "test_id": "tests/test_chaos.py::test_runtime_boot",
            "outcome": "passed",
            "duration_ms": 12.5,
        },
        {
            "test_id": "tests/test_chaos.py::test_bridge_receipt",
            "outcome": "failed",
            "duration_ms": 7.25,
            "message": "assert exported_receipt",
        },
    ]

    artifact_one = build_qube_kernel_test_artifact(
        suite_name="bridge-first-chaos",
        repository="adaptco/A2A_MCP",
        commit_sha="abc123",
        test_results=test_results,
        signing_secret="axis-secret",
        artifact_paths=[log_path],
        generated_at="2026-03-14T12:00:00+00:00",
        metadata={"origin": "bridge-first"},
    )
    artifact_two = build_qube_kernel_test_artifact(
        suite_name="bridge-first-chaos",
        repository="adaptco/A2A_MCP",
        commit_sha="abc123",
        test_results=test_results,
        signing_secret="axis-secret",
        artifact_paths=[log_path],
        generated_at="2026-03-14T12:00:00+00:00",
        metadata={"origin": "bridge-first"},
    )

    assert artifact_one.model_dump(mode="json") == artifact_two.model_dump(mode="json")

    receipt = ChaosTestReceiptV1.model_validate(artifact_one.content)
    assert receipt.status == "failed"
    assert receipt.summary.total == 2
    assert receipt.summary.failed == 1
    assert receipt.axis_token.token_id.startswith("axis-")
    assert receipt.artifact_digests[0].sha256 == hashlib.sha256(log_path.read_bytes()).hexdigest()
    assert verify_axis_token(receipt, signing_secret="axis-secret") is True


def test_verify_axis_token_detects_tampering() -> None:
    artifact = build_qube_kernel_test_artifact(
        suite_name="bridge-first-chaos",
        repository="adaptco/A2A_MCP",
        commit_sha="def456",
        test_results=[
            {
                "test_id": "tests/test_chaos.py::test_smoke",
                "outcome": "passed",
                "duration_ms": 5.0,
            }
        ],
        signing_secret="axis-secret",
        generated_at="2026-03-14T12:00:00+00:00",
    )
    tampered = json.loads(json.dumps(artifact.content))
    tampered["summary"]["passed"] = 99

    assert verify_axis_token(tampered, signing_secret="axis-secret") is False


def test_export_qube_kernel_test_artifact_writes_canonical_payload(
    tmp_path: Path,
) -> None:
    artifact = build_qube_kernel_test_artifact(
        suite_name="bridge-first-chaos",
        repository="adaptco/A2A_MCP",
        commit_sha="fedcba",
        test_results=[
            {
                "test_id": "tests/test_chaos.py::test_export",
                "outcome": "passed",
                "duration_ms": 3.0,
            }
        ],
        signing_secret="axis-secret",
        generated_at="2026-03-14T12:00:00+00:00",
    )
    output_path = tmp_path / "bridge" / "qube-kernel-test-artifact.json"

    export_result = export_qube_kernel_test_artifact(artifact, output_path)

    saved_bytes = output_path.read_bytes()
    saved_payload = json.loads(saved_bytes.decode("utf-8"))
    assert saved_payload["type"] == "chaos.test.receipt.v1"
    assert saved_payload["metadata"]["axis_token_id"] == saved_payload["content"]["axis_token"]["token_id"]
    assert export_result["sha256"] == hashlib.sha256(saved_bytes).hexdigest()
    assert export_result["bytes"] == len(saved_bytes)
