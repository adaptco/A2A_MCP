from __future__ import annotations

import json
from pathlib import Path

import pytest

from core_orchestrator.release_candidate import (
    DriftDetected,
    ProductionReleaseAutomator,
    ReleaseValidationError,
    default_schema_root,
)


@pytest.fixture
def payloads() -> tuple[dict, dict]:
    adapter_input = {
        "adapter_id": "adapter-1",
        "plan_id": "plan-2026-01",
        "candidate_id": "cand-7",
        "payload": {"deploy_window": "nightly"},
        "created_at": "2026-01-02T01:00:00+00:00",
    }
    adapter_output = {
        "adapter_id": "adapter-1",
        "plan_id": "plan-2026-01",
        "candidate_id": "cand-7",
        "status": "approved",
        "summary": "all checks green",
        "decided_at": "2026-01-02T01:30:00+00:00",
        "artifacts": [{"name": "bundle", "uri": "s3://releases/bundle.tar.gz"}],
    }
    return adapter_input, adapter_output


def test_build_release_artifacts_and_write(tmp_path: Path, payloads: tuple[dict, dict]) -> None:
    adapter_input, adapter_output = payloads
    automator = ProductionReleaseAutomator(default_schema_root())

    artifacts = automator.build_release_artifacts(adapter_input, adapter_output)
    automator.write_artifacts(artifacts, tmp_path)

    assert artifacts.gate_result["status"] == "pass"
    assert (tmp_path / "capsule.plan.release.candidate.v1.json").exists()
    persisted_hash = json.loads((tmp_path / "release.hash.plan.release.candidate.v1.json").read_text())
    assert persisted_hash["gate_hash"] == artifacts.gate_hash


def test_assert_expected_hash_raises_drift(payloads: tuple[dict, dict]) -> None:
    adapter_input, adapter_output = payloads
    automator = ProductionReleaseAutomator(default_schema_root())
    artifacts = automator.build_release_artifacts(adapter_input, adapter_output)

    with pytest.raises(DriftDetected, match="gate hash drift detected"):
        automator.assert_expected_hash(artifacts, expected_gate_hash="bad-hash")


def test_invalid_payload_raises_validation_error(payloads: tuple[dict, dict]) -> None:
    adapter_input, adapter_output = payloads
    adapter_input.pop("adapter_id")
    automator = ProductionReleaseAutomator(default_schema_root())

    with pytest.raises(ReleaseValidationError):
        automator.build_release_artifacts(adapter_input, adapter_output)


def test_invalid_datetime_is_rejected(payloads: tuple[dict, dict]) -> None:
    adapter_input, adapter_output = payloads
    adapter_output["decided_at"] = "not-a-datetime"
    automator = ProductionReleaseAutomator(default_schema_root())

    with pytest.raises(ReleaseValidationError, match="date-time"):
        automator.build_release_artifacts(adapter_input, adapter_output)
