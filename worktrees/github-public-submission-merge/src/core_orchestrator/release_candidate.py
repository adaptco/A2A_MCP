"""Utilities for automating production release-candidate capsule generation."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft7Validator, FormatChecker, RefResolver


class ReleaseValidationError(ValueError):
    """Raised when release payloads do not match their schemas."""


class DriftDetected(Exception):
    """Raised when the observed gate hash drifts from the expected hash."""

    def __init__(self, details: Mapping[str, object]) -> None:
        self.details = details
        expected = details.get("expected")
        actual = details.get("actual")
        super().__init__(f"gate hash drift detected (expected={expected}, actual={actual})")


@dataclass(frozen=True)
class ReleaseArtifacts:
    capsule: dict[str, Any]
    gate_result: dict[str, Any]
    gate_hash: str


def default_schema_root() -> Path:
    return Path(__file__).resolve().parents[2] / "schemas"


class ProductionReleaseAutomator:
    """Build, validate, and hash release-candidate capsules."""

    def __init__(self, schema_root: Path | None = None) -> None:
        self._schema_root = schema_root or default_schema_root()
        self._format_checker = self._build_format_checker()
        self._resolver = RefResolver(base_uri=f"{self._schema_root.resolve().as_uri()}/", referrer={})
        self._input_validator = self._validator("adapter.plan.release.candidate.input.v1.schema.json")
        self._output_validator = self._validator("adapter.plan.release.candidate.output.v1.schema.json")
        self._gate_validator = self._validator("gate.result.plan.release.candidate.v1.schema.json")
        self._capsule_validator = self._validator("capsule.plan.release.candidate.v1.schema.json")

    @staticmethod
    def _build_format_checker() -> FormatChecker:
        checker = FormatChecker()

        @checker.checks("date-time")
        def _is_datetime(value: object) -> bool:
            if not isinstance(value, str):
                return False
            candidate = value.replace("Z", "+00:00")
            try:
                datetime.fromisoformat(candidate)
            except ValueError:
                return False
            return True

        return checker

    def _validator(self, schema_name: str) -> Draft7Validator:
        schema = json.loads((self._schema_root / schema_name).read_text())
        return Draft7Validator(schema, format_checker=self._format_checker, resolver=self._resolver)

    def build_release_artifacts(
        self,
        input_payload: Mapping[str, Any],
        output_payload: Mapping[str, Any],
        gate_result: Mapping[str, Any] | None = None,
    ) -> ReleaseArtifacts:
        self._validate(input_payload, self._input_validator, "adapter input")
        self._validate(output_payload, self._output_validator, "adapter output")

        resolved_gate_result = dict(gate_result) if gate_result is not None else self.default_gate_result(output_payload)
        self._validate(resolved_gate_result, self._gate_validator, "gate result")

        capsule = self.build_capsule(input_payload, output_payload)
        self._validate(capsule, self._capsule_validator, "capsule")

        gate_hash = self.compute_gate_hash(input_payload, output_payload, resolved_gate_result)
        return ReleaseArtifacts(capsule=capsule, gate_result=resolved_gate_result, gate_hash=gate_hash)

    def assert_expected_hash(self, artifacts: ReleaseArtifacts, expected_gate_hash: str) -> None:
        if artifacts.gate_hash != expected_gate_hash:
            raise DriftDetected(
                {
                    "expected": expected_gate_hash,
                    "actual": artifacts.gate_hash,
                    "capsule": artifacts.capsule,
                    "gate_result": artifacts.gate_result,
                }
            )

    def write_artifacts(self, artifacts: ReleaseArtifacts, output_dir: Path) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "capsule.plan.release.candidate.v1.json").write_text(
            json.dumps(artifacts.capsule, indent=2, sort_keys=True) + "\n"
        )
        (output_dir / "gate.result.plan.release.candidate.v1.json").write_text(
            json.dumps(artifacts.gate_result, indent=2, sort_keys=True) + "\n"
        )
        (output_dir / "release.hash.plan.release.candidate.v1.json").write_text(
            json.dumps({"gate_hash": artifacts.gate_hash}, indent=2, sort_keys=True) + "\n"
        )

    def build_capsule(
        self,
        input_payload: Mapping[str, Any],
        output_payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        return {
            "capsule_id": "capsule.plan.release.candidate.v1",
            "schema_version": "capsule.plan.release.candidate.v1",
            "input": dict(input_payload),
            "output": dict(output_payload),
            "input_hash": self.sha256_canonical(input_payload),
            "output_hash": self.sha256_canonical(output_payload),
            "sealed_at": datetime.now(tz=UTC).isoformat(),
        }

    def compute_gate_hash(
        self,
        input_payload: Mapping[str, Any],
        output_payload: Mapping[str, Any],
        gate_result: Mapping[str, Any],
    ) -> str:
        capsule_hash = self.sha256_canonical(
            {
                "input_hash": self.sha256_canonical(input_payload),
                "output_hash": self.sha256_canonical(output_payload),
            }
        )
        return self.sha256_canonical(
            {
                "capsule_hash": capsule_hash,
                "gate_result": gate_result,
            }
        )

    def default_gate_result(self, output_payload: Mapping[str, Any]) -> dict[str, Any]:
        is_pass = output_payload.get("status") == "approved"
        return {
            "gate_id": "release-candidate-auto-gate",
            "status": "pass" if is_pass else "fail",
            "evaluated_at": datetime.now(tz=UTC).isoformat(),
            "violations": [] if is_pass else ["release candidate was not approved"],
            "metrics": {"artifact_count": len(output_payload.get("artifacts", []))},
        }

    def _validate(self, payload: Mapping[str, Any], validator: Draft7Validator, payload_name: str) -> None:
        errors = sorted(validator.iter_errors(payload), key=lambda err: list(err.absolute_path))
        if not errors:
            return
        details = [f"{payload_name}: {error.message}" for error in errors]
        raise ReleaseValidationError("; ".join(details))

    @staticmethod
    def sha256_canonical(payload: Mapping[str, Any]) -> str:
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
