"""Runtime interfaces for generated agents."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


class ActuatorClient:
    """Base implementation for actuator-capable agents."""

    def load_contract(self, path: str | Path) -> dict[str, Any]:
        return json.loads(Path(path).read_text(encoding="utf-8"))

    def validate(self, contract: dict[str, Any], schema: dict[str, Any]) -> None:
        Draft202012Validator(schema).validate(contract)

    def execute(self, contract: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
        return {"contract": contract, "state": state, "status": "executed"}

    def emit_artifacts(self, artifacts: dict[str, Any], output_path: str | Path) -> Path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(artifacts, indent=2), encoding="utf-8")
        return out


class RouterClient:
    """Base implementation for trajectory arbitration."""

    def compute_cost(self, trajectory: dict[str, float], weights: dict[str, float]) -> float:
        return sum(trajectory.get(metric, 0.0) * weight for metric, weight in weights.items())

    def enforce_invariants(self, state: dict[str, Any], required_invariants: list[str]) -> bool:
        present = set(state.get("invariants", []))
        return set(required_invariants).issubset(present)

    def select_trajectory(self, candidates: list[dict[str, Any]]) -> dict[str, Any]:
        if not candidates:
            raise ValueError("No candidate trajectories supplied")
        return min(candidates, key=lambda candidate: candidate.get("cost", float("inf")))
