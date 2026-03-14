"""Golden Capsule Test replay harness for plan release candidate adapters."""
from __future__ import annotations

from typing import Callable, Mapping

from core_orchestrator.release_candidate import (
    DriftDetected,
    ProductionReleaseAutomator,
    default_schema_root,
)


def replay_golden_capsule(
    input_payload: Mapping[str, object],
    run_adapter: Callable[[Mapping[str, object]], Mapping[str, object]],
    run_gate: Callable[[Mapping[str, object]], Mapping[str, object]],
    expected_gate_hash: str,
) -> str:
    """Replay the golden capsule and assert deterministic gate hashing."""
    automator = ProductionReleaseAutomator(default_schema_root())
    output = run_adapter(input_payload)
    capsule = automator.build_capsule(input_payload, output)
    gate_result = run_gate(capsule)

    artifacts = automator.build_release_artifacts(input_payload, output, gate_result)
    automator.assert_expected_hash(artifacts, expected_gate_hash)
    return artifacts.gate_hash


def build_capsule(
    input_payload: Mapping[str, object],
    output_payload: Mapping[str, object],
) -> dict[str, object]:
    automator = ProductionReleaseAutomator(default_schema_root())
    return automator.build_capsule(input_payload, output_payload)


def compute_gate_hash(
    input_payload: Mapping[str, object],
    output_payload: Mapping[str, object],
    gate_result: Mapping[str, object],
) -> str:
    automator = ProductionReleaseAutomator(default_schema_root())
    return automator.compute_gate_hash(input_payload, output_payload, gate_result)


def sha256_canonical(payload: Mapping[str, object]) -> str:
    return ProductionReleaseAutomator.sha256_canonical(payload)


__all__ = [
    "DriftDetected",
    "build_capsule",
    "compute_gate_hash",
    "replay_golden_capsule",
    "sha256_canonical",
]
