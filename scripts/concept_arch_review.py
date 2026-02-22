#!/usr/bin/env python3
"""Runbook automation for the Conceptual Architecture Review capsule."""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any, Iterable

TRACE_PATH = Path("ledger/concept_arch_review.jsonl")
DEFAULT_MANIFEST = Path("capsules/governance/capsule.concept.arch.review.v1.json")
DEFAULT_SCHEMA = Path("specs/capsule.concept.arch.review.v1.schema.json")
DEFAULT_SCENARIO_ROOT = Path("manifests/concept_architecture")
ABS_TOLERANCE = 1e-9


class ReviewError(RuntimeError):
    """Raised when a guard or invariant fails."""


def load_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError as exc:  # pragma: no cover - surfaced to CLI
        raise ReviewError(f"File not found: {path}") from exc
    except json.JSONDecodeError as exc:  # pragma: no cover - surfaced to CLI
        raise ReviewError(f"Invalid JSON in {path}: {exc}") from exc


def ensure(condition: bool, message: str) -> None:
    if not condition:
        raise ReviewError(message)


def nearly_equal(value: float, target: float) -> bool:
    return abs(value - target) <= ABS_TOLERANCE


def validate_manifest_schema(manifest: dict[str, Any], schema_path: Path) -> None:
    schema = load_json(schema_path)
    try:
        from jsonschema import Draft7Validator
    except ModuleNotFoundError as exc:  # pragma: no cover - dependency resolution issue
        raise ReviewError(
            "jsonschema dependency missing – install with `pip install jsonschema`"
        ) from exc

    validator = Draft7Validator(schema)
    errors = sorted(validator.iter_errors(manifest), key=lambda err: err.path)
    if errors:
        formatted = ", ".join(
            f"{'/'.join(str(segment) for segment in error.absolute_path) or '<root>'}: {error.message}"
            for error in errors
        )
        raise ReviewError(f"Manifest violates schema: {formatted}")


def validate_manifest(manifest: dict[str, Any]) -> None:
    ensure(isinstance(manifest, dict), "Manifest must be a JSON object")
    ensure(manifest.get("capsule_id") == "capsule.concept.arch.review.v1", "capsule_id mismatch")
    version = manifest.get("version")
    ensure(isinstance(version, str) and version.count(".") == 2, "version must be semantic (x.y.z)")
    ensure(manifest.get("intent") == "stability_vs_evolution", "intent must be stability_vs_evolution")

    envelope = manifest.get("envelope")
    ensure(isinstance(envelope, dict), "envelope must be defined")
    for key in ("epsilon_c", "epsilon_c_max", "B_m", "r_min", "t_canary_sec", "rollback_window_sec"):
        ensure(key in envelope, f"envelope.{key} missing")
    ensure(0 < envelope["epsilon_c"] < envelope["epsilon_c_max"], "epsilon_c must be >0 and < epsilon_c_max")
    ensure(envelope["B_m"] > 0, "B_m must be positive")
    ensure(0 <= envelope["r_min"] <= 1, "r_min must be between 0 and 1")
    ensure(envelope["t_canary_sec"] >= 1, "t_canary_sec must be positive")
    ensure(envelope["rollback_window_sec"] >= 1, "rollback_window_sec must be positive")

    weights = manifest.get("weights")
    ensure(isinstance(weights, dict), "weights must be defined")
    for key in ("w_v", "w_c", "w_o", "w_r", "s_min"):
        ensure(key in weights, f"weights.{key} missing")

    guards = manifest.get("guards")
    ensure(isinstance(guards, list) and guards, "guards must be a non-empty list")
    ensure("ΔΦe==0" in guards, "guards must explicitly lock ΔΦe==0")

    raci = manifest.get("raci")
    ensure(isinstance(raci, list) and len(raci) >= 4, "raci must list at least 4 roles")
    required_roles = {"Gloh:maker", "Spryte:checker", "Glyph.Trace:auditor", "Echo.Mesh:relay"}
    ensure(required_roles.issubset(raci), "raci must include maker/checker/auditor/relay anchors")
    ensure(any(entry.startswith("Council:") for entry in raci), "raci must encode Council quorum")

    attestation = manifest.get("attestation")
    ensure(isinstance(attestation, dict), "attestation must be defined")
    ensure(attestation.get("status") in {"STAGED", "SEALED"}, "attestation.status must be STAGED or SEALED")


def guard_zero_delta_phi_e(value: float) -> None:
    ensure(nearly_equal(value, 0.0), f"ΔΦₑ must remain 0 (observed {value})")


def guard_reversibility(value: float, minimum: float) -> None:
    ensure(value >= minimum, f"Reversibility {value} below minimum {minimum}")


def guard_phi_c(value: float, epsilon_c: float, epsilon_c_max: float) -> None:
    ensure(value <= epsilon_c_max + ABS_TOLERANCE, f"ΔΦ_c {value} exceeds ε_c,max {epsilon_c_max}")
    ensure(value <= epsilon_c + ABS_TOLERANCE, f"ΔΦ_c {value} exceeds ε_c envelope {epsilon_c}")


def guard_phi_m(value: float, budget: float) -> None:
    ensure(value <= budget + ABS_TOLERANCE, f"Φ_m {value} exceeds budget {budget}")


def append_trace(
    manifest: dict[str, Any],
    action: str,
    scenario_path: Path,
    payload: dict[str, Any],
) -> None:
    TRACE_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
        "capsule_id": manifest["capsule_id"],
        "version": manifest["version"],
        "action": action,
        "scenario": str(scenario_path),
        "payload": payload,
    }
    with TRACE_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def handle_review(args: argparse.Namespace, manifest: dict[str, Any]) -> dict[str, Any]:
    scenario_path = Path(args.scenario)
    scenario = load_json(scenario_path)
    envelope = manifest["envelope"]
    weights = manifest["weights"]

    required = ("delta_phi_e", "delta_phi_c", "delta_phi_m", "pi_v", "ops_cost", "reversibility")
    for key in required:
        ensure(key in scenario, f"review scenario missing {key}")

    guard_zero_delta_phi_e(float(scenario["delta_phi_e"]))
    guard_phi_c(float(scenario["delta_phi_c"]), envelope["epsilon_c"], envelope["epsilon_c_max"])
    guard_phi_m(float(scenario["delta_phi_m"]), envelope["B_m"])
    guard_reversibility(float(scenario["reversibility"]), envelope["r_min"])

    score = (
        weights["w_v"] * float(scenario["pi_v"])
        - weights["w_c"] * float(scenario["delta_phi_c"])
        - weights["w_o"] * float(scenario["ops_cost"])
        + weights["w_r"] * float(scenario["reversibility"])
    )
    promotable = score >= weights["s_min"]

    result = {
        "proposal_id": scenario.get("proposal_id"),
        "score": round(score, 6),
        "promotable": promotable,
        "guards": "pass",
        "notes": scenario.get("notes"),
    }
    append_trace(manifest, "review", scenario_path, result)
    return result


def max_sample(values: Iterable[Any]) -> float:
    casted = [float(value) for value in values]
    ensure(casted, "Sample list cannot be empty")
    return max(casted)


def handle_canary(args: argparse.Namespace, manifest: dict[str, Any]) -> dict[str, Any]:
    scenario_path = Path(args.scenario)
    scenario = load_json(scenario_path)
    envelope = manifest["envelope"]

    ensure("canary_size" in scenario, "canary scenario must include canary_size")
    ensure(float(scenario["canary_size"]) <= 0.1 + ABS_TOLERANCE, "Canary size must be ≤10% of blast radius")

    delta_phi_e_samples = scenario.get("delta_phi_e_samples", {})
    ensure(isinstance(delta_phi_e_samples, dict), "delta_phi_e_samples must be a mapping of windows")
    for window in ("1s", "10s", "60s"):
        ensure(window in delta_phi_e_samples, f"ΔΦₑ sample missing {window} window")
        guard_zero_delta_phi_e(float(delta_phi_e_samples[window]))

    delta_phi_c_samples = scenario.get("delta_phi_c_samples")
    ensure(isinstance(delta_phi_c_samples, list), "delta_phi_c_samples must be a list")
    peak_phi_c = max_sample(delta_phi_c_samples)
    guard_phi_c(peak_phi_c, envelope["epsilon_c"], envelope["epsilon_c_max"])

    delta_phi_m_samples = scenario.get("delta_phi_m_samples")
    ensure(isinstance(delta_phi_m_samples, list), "delta_phi_m_samples must be a list")
    peak_phi_m = max_sample(delta_phi_m_samples)
    guard_phi_m(peak_phi_m, envelope["B_m"])

    reversibility = float(scenario.get("reversibility", 0.0))
    guard_reversibility(reversibility, envelope["r_min"])

    result = {
        "proposal_id": scenario.get("proposal_id"),
        "peak_phi_c": peak_phi_c,
        "peak_phi_m": peak_phi_m,
        "reversibility": reversibility,
        "status": "stable",
        "notes": scenario.get("notes"),
    }
    append_trace(manifest, "canary", scenario_path, result)
    return result


def handle_promote(args: argparse.Namespace, manifest: dict[str, Any]) -> dict[str, Any]:
    scenario_path = Path(args.scenario)
    scenario = load_json(scenario_path)
    envelope = manifest["envelope"]

    ensure("canary_duration_sec" in scenario, "promote scenario must include canary_duration_sec")
    ensure(int(scenario["canary_duration_sec"]) >= envelope["t_canary_sec"], "Canary duration shorter than required window")
    guard_zero_delta_phi_e(float(scenario.get("delta_phi_e", 0.0)))
    guard_phi_c(float(scenario.get("phi_c_post", 0.0)), envelope["epsilon_c"], envelope["epsilon_c_max"])
    guard_phi_m(float(scenario.get("phi_m_current", 0.0)), envelope["B_m"])
    ensure(int(scenario.get("council_quorum", 0)) >= 3, "Council quorum must be ≥3")

    pi_v_attested = float(scenario.get("pi_v_attested", 0.0))
    result = {
        "proposal_id": scenario.get("proposal_id"),
        "pi_v_attested": pi_v_attested,
        "canary_duration_sec": int(scenario["canary_duration_sec"]),
        "status": "promoted",
        "notes": scenario.get("notes"),
    }
    append_trace(manifest, "promote", scenario_path, result)
    return result


def handle_rollback(args: argparse.Namespace, manifest: dict[str, Any]) -> dict[str, Any]:
    scenario_path = Path(args.scenario)
    scenario = load_json(scenario_path)
    envelope = manifest["envelope"]

    ensure("elapsed_sec" in scenario, "rollback scenario must include elapsed_sec")
    ensure(float(scenario["elapsed_sec"]) <= envelope["rollback_window_sec"], "Rollback exceeded τ_R window")

    delta_phi_e = float(scenario.get("delta_phi_e", 0.0))
    ensure(delta_phi_e > 0.0, "Rollback requires ΔΦₑ spike > 0")

    result = {
        "proposal_id": scenario.get("proposal_id"),
        "trigger_guard": scenario.get("trigger_guard"),
        "elapsed_sec": float(scenario["elapsed_sec"]),
        "delta_phi_e": delta_phi_e,
        "status": "rolled_back",
        "notes": scenario.get("notes"),
    }
    append_trace(manifest, "rollback", scenario_path, result)
    return result


def handle_fossilize(args: argparse.Namespace, manifest: dict[str, Any]) -> dict[str, Any]:
    scenario_path = Path(args.scenario)
    scenario = load_json(scenario_path)

    signatures = scenario.get("council_signatures")
    ensure(isinstance(signatures, list) and len(signatures) >= 3, "At least three council signatures required")
    raci_set = set(manifest.get("raci", []))
    for signer in signatures:
        ensure(isinstance(signer, str), "Signatures must be strings")
        ensure(
            signer in raci_set,
            f"Signature {signer} not recognized in capsule RACI",
        )

    attestation_status = scenario.get("attestation_status")
    ensure(attestation_status == "SEALED", "attestation_status must be SEALED")

    result = {
        "proposal_id": scenario.get("proposal_id"),
        "council_signatures": signatures,
        "attestation_status": attestation_status,
        "status": "fossilized",
        "notes": scenario.get("notes"),
    }
    append_trace(manifest, "fossilize", scenario_path, result)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        default=str(DEFAULT_MANIFEST),
        help="Path to the Conceptual Architecture Review manifest",
    )
    parser.add_argument(
        "--schema",
        default=str(DEFAULT_SCHEMA),
        help="Path to the JSON schema used to validate the manifest",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_subparser(name: str, default_scenario: str) -> argparse.ArgumentParser:
        subparser = subparsers.add_parser(name, help=f"Run the {name} stage")
        subparser.add_argument(
            "--scenario",
            default=str(DEFAULT_SCENARIO_ROOT / default_scenario),
            help="Path to the scenario payload JSON",
        )
        return subparser

    add_subparser("review", "review.json")
    add_subparser("canary", "canary.json")
    add_subparser("promote", "promote.json")
    add_subparser("rollback", "rollback.json")
    add_subparser("fossilize", "fossilize.json")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    manifest_path = Path(args.manifest)
    manifest = load_json(manifest_path)
    schema_path = Path(args.schema)
    validate_manifest_schema(manifest, schema_path)
    validate_manifest(manifest)

    handlers = {
        "review": handle_review,
        "canary": handle_canary,
        "promote": handle_promote,
        "rollback": handle_rollback,
        "fossilize": handle_fossilize,
    }

    handler = handlers[args.command]
    result = handler(args, manifest)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":  # pragma: no cover
    import sys

    try:
        raise SystemExit(main())
    except ReviewError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
