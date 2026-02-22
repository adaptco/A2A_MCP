"""Golden Capsule Test replay harness for plan release candidate adapters."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Mapping
import hashlib
import json


@dataclass(frozen=True)
class DriftDetected(Exception):
    details: Mapping[str, object]


def replay_golden_capsule(
    input_payload: Mapping[str, object],
    run_adapter: Callable[[Mapping[str, object]], Mapping[str, object]],
    run_gate: Callable[[Mapping[str, object]], Mapping[str, object]],
    expected_gate_hash: str,
) -> str:
    """Replay the golden capsule and assert deterministic gate hashing."""
    output = run_adapter(input_payload)
    capsule = build_capsule(input_payload, output)
    gate_result = run_gate(capsule)
    gate_hash = compute_gate_hash(input_payload, output, gate_result)

    if gate_hash != expected_gate_hash:
        raise DriftDetected(
            {
                "expected": expected_gate_hash,
                "actual": gate_hash,
                "capsule": capsule,
                "gate_result": gate_result,
            }
        )

    return gate_hash


def build_capsule(
    input_payload: Mapping[str, object],
    output_payload: Mapping[str, object],
) -> Dict[str, object]:
    input_hash = sha256_canonical(input_payload)
    output_hash = sha256_canonical(output_payload)
    return {
        "capsule_id": "capsule.plan.release.candidate.v1",
        "schema_version": "capsule.plan.release.candidate.v1",
        "input": input_payload,
        "output": output_payload,
        "input_hash": input_hash,
        "output_hash": output_hash,
        "sealed_at": "0000-00-00T00:00:00Z",
    }


def compute_gate_hash(
    input_payload: Mapping[str, object],
    output_payload: Mapping[str, object],
    gate_result: Mapping[str, object],
) -> str:
    capsule_hash = sha256_canonical(
        {
            "input_hash": sha256_canonical(input_payload),
            "output_hash": sha256_canonical(output_payload),
        }
    )
    return sha256_canonical(
        {
            "capsule_hash": capsule_hash,
            "gate_result": gate_result,
        }
    )


def sha256_canonical(payload: Mapping[str, object]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
