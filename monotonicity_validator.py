"""Monotonicity validator for warehouse-physics avatar training artifacts.

The validator enforces immutable rendering/physics invariants and supports three
modes:
- hard_reject: fail immediately on any drift
- soft_projection: force all invariant fields back to constitutional values
- hybrid: project minor value drift, reject structural drift (missing fields)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Mapping, MutableMapping

INVARIANTS: Dict[str, Any] = {
    "wheel_spokes": 5,
    "wheel_finish": "RSM",
    "body_color": "obsidian_black",
    "fov": 60,
    "stroke_color": "#18D8EF",
}


class ValidatorMode(str, Enum):
    HARD_REJECT = "hard_reject"
    SOFT_PROJECTION = "soft_projection"
    HYBRID = "hybrid"


@dataclass
class MonotonicityResult:
    passed: bool
    mode: str
    violations: List[str]
    projected_state: Dict[str, Any]


class MonotonicityValidationError(ValueError):
    """Raised when hard invariant checks fail and cannot be projected."""


class MonotonicityValidator:
    def __init__(
        self,
        invariants: Mapping[str, Any] | None = None,
        *,
        mode: ValidatorMode = ValidatorMode.HYBRID,
    ) -> None:
        self.invariants: Dict[str, Any] = dict(invariants or INVARIANTS)
        self.mode = mode

    def evaluate(self, candidate_state: Mapping[str, Any]) -> MonotonicityResult:
        projected = self._project(candidate_state)
        violations: List[str] = []
        missing_keys: List[str] = []

        for key, expected in self.invariants.items():
            if key not in candidate_state:
                missing_keys.append(key)
                violations.append(f"missing invariant field '{key}'")
                continue

            got = candidate_state[key]
            if got != expected:
                violations.append(
                    f"invariant drift for '{key}': expected={expected!r} actual={got!r}"
                )

        passed = self._passes_by_mode(violations=violations, missing_keys=missing_keys)
        return MonotonicityResult(
            passed=passed,
            mode=self.mode.value,
            violations=violations,
            projected_state=projected,
        )

    def enforce(self, candidate_state: Mapping[str, Any]) -> Dict[str, Any]:
        result = self.evaluate(candidate_state)
        if not result.passed:
            raise MonotonicityValidationError("; ".join(result.violations))
        return result.projected_state

    def _project(self, candidate_state: Mapping[str, Any]) -> Dict[str, Any]:
        projected: MutableMapping[str, Any] = dict(candidate_state)
        for key, expected in self.invariants.items():
            projected[key] = expected
        return dict(projected)

    def _passes_by_mode(self, *, violations: List[str], missing_keys: List[str]) -> bool:
        if not violations:
            return True

        if self.mode == ValidatorMode.HARD_REJECT:
            return False

        if self.mode == ValidatorMode.SOFT_PROJECTION:
            return True

        # Hybrid mode: structural drift (missing invariants) is rejected,
        # while value drift is tolerated through projection.
        return not missing_keys


def validate_candidate_state(
    candidate_state: Mapping[str, Any],
    *,
    mode: ValidatorMode = ValidatorMode.HYBRID,
    invariants: Mapping[str, Any] | None = None,
) -> MonotonicityResult:
    """Convenience helper for one-shot validation calls."""

    return MonotonicityValidator(invariants=invariants, mode=mode).evaluate(candidate_state)
