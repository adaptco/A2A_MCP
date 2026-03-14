import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


@dataclass
class InvariantResult:
    invariant_id: str
    verdict: str
    hard_fail: bool
    details: str


class InvariantViolation(Exception):
    pass


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def env_true(name: str, default: str = "false") -> bool:
    return os.environ.get(name, default).strip().lower() in {"1", "true", "yes", "on"}


def check_pr_only_output_policy(criteria: dict[str, Any]) -> tuple[bool, str]:
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")
    output_channel = os.environ.get("AUTOMATION_OUTPUT_CHANNEL", "pr")
    automation_events = set(criteria.get("automation_events", []))

    if event_name in automation_events and output_channel != "pr":
        return False, (
            f"automation event '{event_name}' must emit PR-only output; "
            f"AUTOMATION_OUTPUT_CHANNEL={output_channel!r}"
        )

    return True, (
        f"event={event_name or 'unknown'}, output_channel={output_channel}, "
        f"automation_events={sorted(automation_events)}"
    )


def check_hermetic_fingerprint(criteria: dict[str, Any]) -> tuple[bool, str]:
    target_file = Path(criteria["fingerprint_file"])
    expected = criteria["router_pinned_sha256"]
    actual = sha256_file(target_file)
    ok = actual == expected
    return ok, f"file={target_file}, actual_sha256={actual}, expected_sha256={expected}"


def check_no_outbound_network(criteria: dict[str, Any]) -> tuple[bool, str]:
    hermetic_env = criteria.get("hermetic_mode_env", "HERMETIC_MODE")
    blocked_env = criteria.get("network_blocked_env", "NO_OUTBOUND_NETWORK")
    hermetic_mode = env_true(hermetic_env)

    if not hermetic_mode:
        return True, f"{hermetic_env}=false; invariant not applicable"

    blocked = env_true(blocked_env)
    allow_override = env_true("ALLOW_OUTBOUND_NETWORK", "false")

    ok = blocked and not allow_override
    return ok, (
        f"{hermetic_env}=true, {blocked_env}={blocked}, "
        f"ALLOW_OUTBOUND_NETWORK={allow_override}"
    )


def check_secret_scan_gate(criteria: dict[str, Any]) -> tuple[bool, str]:
    pathspecs = criteria.get("paths", ["."])
    ignore = set(criteria.get("ignore", []))
    patterns = [re.compile(expr) for expr in criteria.get("patterns", [])]

    tracked = subprocess.check_output(["git", "ls-files", *pathspecs], text=True).splitlines()
    hits: list[str] = []

    for rel in tracked:
        if rel in ignore:
            continue
        file_path = Path(rel)
        if not file_path.exists() or file_path.is_dir():
            continue
        stop_scanning = False
        try:
            with file_path.open(encoding="utf-8") as f:
                for idx, line in enumerate(f, start=1):
                    if any(p.search(line) for p in patterns):
                        hits.append(f"{rel}:{idx}")
                        if len(hits) >= 20:
                            stop_scanning = True
                            break
        except UnicodeDecodeError:
            continue

        if stop_scanning:
            break

    if hits:
        return False, f"Potential secret patterns found at: {hits}"
    return True, f"Scanned {len(tracked)} tracked files with no secret-pattern matches."


def check_policy_zoning(criteria: dict[str, Any]) -> tuple[bool, str]:
    min_reviewers = criteria.get("min_reviewers")
    required_checks = criteria.get("required_checks", [])

    ok = isinstance(min_reviewers, int) and min_reviewers >= 1 and bool(required_checks)
    return ok, (
        f"min_reviewers={min_reviewers}, required_checks={required_checks}"
    )


def check_deterministic_artifact_hash(criteria: dict[str, Any]) -> tuple[bool, str]:
    artifact_path = Path(criteria["artifact_path"])
    expected = criteria["expected_sha256"]
    actual = sha256_file(artifact_path)
    ok = actual == expected
    return ok, f"file={artifact_path}, actual_sha256={actual}, expected_sha256={expected}"


CHECKERS = {
    "INV-PR-ONLY-AUTOMATION-OUTPUT": check_pr_only_output_policy,
    "INV-HERMETIC-FINGERPRINT": check_hermetic_fingerprint,
    "INV-HERMETIC-NO-NETWORK": check_no_outbound_network,
    "INV-SECRET-SCAN-GATE": check_secret_scan_gate,
    "INV-POLICY-ZONING-QUORUM": check_policy_zoning,
    "INV-DETERMINISTIC-ARTIFACT-HASH": check_deterministic_artifact_hash,
}


def evaluate_invariants(registry: dict[str, Any]) -> list[InvariantResult]:
    results: list[InvariantResult] = []
    for invariant in registry.get("locked_invariants", []):
        invariant_id = invariant["id"]
        hard_fail = bool(invariant.get("hard_fail", True))
        checker = CHECKERS.get(invariant_id)

        if checker is None:
            results.append(
                InvariantResult(
                    invariant_id=invariant_id,
                    verdict="fail",
                    hard_fail=hard_fail,
                    details="No checker implemented for invariant ID.",
                )
            )
            continue

        ok, details = checker(invariant.get("criteria", {}))
        results.append(
            InvariantResult(
                invariant_id=invariant_id,
                verdict="pass" if ok else "fail",
                hard_fail=hard_fail,
                details=details,
            )
        )

    return results


def check_pr_only_output_policy(criteria: dict[str, Any]) -> tuple[bool, str]:
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")
    output_channel = os.environ.get("AUTOMATION_OUTPUT_CHANNEL", "pr")
    automation_events = set(criteria.get("automation_events", []))

    if event_name in automation_events and output_channel != "pr":
        return False, (
            f"automation event '{event_name}' must emit PR-only output; "
            f"AUTOMATION_OUTPUT_CHANNEL={output_channel!r}"
        )
    )

    return True, (
        f"event={event_name or 'unknown'}, output_channel={output_channel}, "
        f"automation_events={sorted(automation_events)}"
    )


def check_hermetic_fingerprint(criteria: dict[str, Any]) -> tuple[bool, str]:
    target_file = Path(criteria["fingerprint_file"])
    expected = criteria["router_pinned_sha256"]
    actual = sha256_file(target_file)
    ok = actual == expected
    return ok, f"file={target_file}, actual_sha256={actual}, expected_sha256={expected}"


def check_no_outbound_network(criteria: dict[str, Any]) -> tuple[bool, str]:
    hermetic_env = criteria.get("hermetic_mode_env", "HERMETIC_MODE")
    blocked_env = criteria.get("network_blocked_env", "NO_OUTBOUND_NETWORK")
    hermetic_mode = env_true(hermetic_env)

    if not hermetic_mode:
        return True, f"{hermetic_env}=false; invariant not applicable"

    blocked = env_true(blocked_env)
    allow_override = env_true("ALLOW_OUTBOUND_NETWORK", "false")

    ok = blocked and not allow_override
    return ok, (
        f"{hermetic_env}=true, {blocked_env}={blocked}, "
        f"ALLOW_OUTBOUND_NETWORK={allow_override}"
    )


def check_secret_scan_gate(criteria: dict[str, Any]) -> tuple[bool, str]:
    pathspecs = criteria.get("paths", ["."])
    ignore = set(criteria.get("ignore", []))
    patterns = [re.compile(expr) for expr in criteria.get("patterns", [])]

    tracked = subprocess.check_output(["git", "ls-files", *pathspecs], text=True).splitlines()
    hits: list[str] = []

    for rel in tracked:
        if rel in ignore:
            continue
        file_path = Path(rel)
        if not file_path.exists() or file_path.is_dir():
            continue
        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        for idx, line in enumerate(content.splitlines(), start=1):
            if any(p.search(line) for p in patterns):
                hits.append(f"{rel}:{idx}")
                if len(hits) >= 20:
                    break
        if len(hits) >= 20:
            break

    if hits:
        return False, f"Potential secret patterns found at: {hits}"
    return True, f"Scanned {len(tracked)} tracked files with no secret-pattern matches."


def check_policy_zoning(criteria: dict[str, Any]) -> tuple[bool, str]:
    min_reviewers = criteria.get("min_reviewers")
    required_checks = criteria.get("required_checks", [])

    ok = isinstance(min_reviewers, int) and min_reviewers >= 1 and bool(required_checks)
    return ok, (
        f"min_reviewers={min_reviewers}, required_checks={required_checks}"
    )


def check_deterministic_artifact_hash(criteria: dict[str, Any]) -> tuple[bool, str]:
    artifact_path = Path(criteria["artifact_path"])
    expected = criteria["expected_sha256"]
    actual = sha256_file(artifact_path)
    ok = actual == expected
    return ok, f"file={artifact_path}, actual_sha256={actual}, expected_sha256={expected}"


CHECKERS = {
    "INV-PR-ONLY-AUTOMATION-OUTPUT": check_pr_only_output_policy,
    "INV-HERMETIC-FINGERPRINT": check_hermetic_fingerprint,
    "INV-HERMETIC-NO-NETWORK": check_no_outbound_network,
    "INV-SECRET-SCAN-GATE": check_secret_scan_gate,
    "INV-POLICY-ZONING-QUORUM": check_policy_zoning,
    "INV-DETERMINISTIC-ARTIFACT-HASH": check_deterministic_artifact_hash,
}


def evaluate_invariants(registry: dict[str, Any]) -> list[InvariantResult]:
    results: list[InvariantResult] = []
    for invariant in registry.get("locked_invariants", []):
        invariant_id = invariant["id"]
        hard_fail = bool(invariant.get("hard_fail", True))
        checker = CHECKERS.get(invariant_id)

        if checker is None:
            results.append(
                InvariantResult(
                    invariant_id=invariant_id,
                    verdict="fail",
                    hard_fail=hard_fail,
                    details="No checker implemented for invariant ID.",
                )
            )
            continue

        ok, details = checker(invariant.get("criteria", {}))
        results.append(
            InvariantResult(
                invariant_id=invariant_id,
                verdict="pass" if ok else "fail",
                hard_fail=hard_fail,
                details=details,
            )
        )

    return results


def check_actuation_contract(contract_path: Path) -> None:
    contract = load_json(contract_path)

    for key in ("actuation_payload_defaults", "cost_weights", "invariants"):
        if key not in contract:
            raise ValueError(f"Actuation contract missing top-level key: {key}")

    defaults = contract["actuation_payload_defaults"]
    for required in (
        "trigger_reason",
        "mode",
        "policy_zone",
        "max_entropy_budget",
        "acceptance_invariants",
    ):
        if required not in defaults:
            raise ValueError(f"actuation_payload_defaults missing required key: {required}")

    enums = contract.get("enums", {})
    for enum_key in ("trigger_reason", "mode", "policy_zone"):
        allowed = set(enums.get(enum_key, []))
        if not allowed:
            raise ValueError(f"Missing enum values for {enum_key}")
        if defaults[enum_key] not in allowed:
            raise ValueError(
                f"Default {enum_key} value '{defaults[enum_key]}' is not in enums.{enum_key}"
            )

    if defaults["policy_zone"] == "hermetic" and defaults["max_entropy_budget"] != 0:
        raise ValueError("Hermetic policy zone requires max_entropy_budget to be exactly 0")

    accepted = set(defaults.get("acceptance_invariants", []))
    missing_acceptance = LOCKED_INVARIANT_IDS - accepted
    if missing_acceptance:
        raise ValueError(
            "acceptance_invariants missing locked invariant IDs: "
            f"{', '.join(sorted(missing_acceptance))}"
        )

    invariant_map = contract["invariants"]
    missing_defs = LOCKED_INVARIANT_IDS - set(invariant_map.keys())
    if missing_defs:
        raise ValueError(
            "invariants map missing locked invariant definitions: "
            f"{', '.join(sorted(missing_defs))}"
        )

    unlocked = [
        inv_id for inv_id in LOCKED_INVARIANT_IDS if not invariant_map[inv_id].get("locked")
    ]
    if unlocked:
        raise ValueError(
            f"Locked invariant IDs must set locked=true: {', '.join(sorted(unlocked))}"
        )


def check_pr_template_registry(registry_path: Path) -> None:
    registry = load_json(registry_path)
    templates = registry.get("templates", {})
    template = templates.get("PRT.AUTO_REPAIR.V1")
    if not template:
        raise ValueError("Template registry missing PRT.AUTO_REPAIR.V1")

    template_path = Path(template.get("path", ""))
    if not template_path.exists():
        raise ValueError(
            "PRT.AUTO_REPAIR.V1 path does not exist: " f"{template_path}"
        )

    body = template_path.read_text()
    if "# PRT.AUTO_REPAIR.V1" not in body:
        raise ValueError("PRT.AUTO_REPAIR.V1 template file missing required header")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate locked CI invariants from registry.")
    parser.add_argument(
        "--registry",
        type=Path,
        default=Path("manifests/invariant_registry.json"),
        help="Path to invariant registry JSON.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional path to write invariant results JSON.",
    )

    return InvariantResult(
        invariant_id=invariant["id"],
        name=invariant["name"],
        hard=bool(invariant.get("hard", True)),
        passed=passed,
        details=details,
        evidence={
            "hermetic_mode": hermetic_mode,
            "outbound_network_allowed": outbound_allowed,
        },
    )


def _check_secret_scan_gate(env: dict[str, str], invariant: dict[str, Any]) -> InvariantResult:
    secret_scan_status = env.get("SECRET_SCAN_STATUS", "").strip().lower()
    passing_values = {value.lower() for value in invariant.get("passing_values", ["pass", "passed", "success"])}

    passed = secret_scan_status in passing_values
    details = (
        "Secret scan gate passed."
        if passed
        else f"Secret scan gate failed with status '{secret_scan_status or 'missing'}'."
    )

    return InvariantResult(
        invariant_id=invariant["id"],
        name=invariant["name"],
        hard=bool(invariant.get("hard", True)),
        passed=passed,
        details=details,
        evidence={
            "secret_scan_status": secret_scan_status,
            "passing_values": sorted(passing_values),
        },
    )


def _check_policy_zoning_quorum(env: dict[str, str], invariant: dict[str, Any]) -> InvariantResult:
    approvals = _as_int(env.get("POLICY_ZONE_APPROVALS"))
    quorum = _as_int(env.get("POLICY_ZONE_QUORUM"))
    required_checks = _as_bool(env.get("POLICY_REQUIRED_CHECKS_PASSED"), default=False)

    has_quorum = approvals is not None and quorum is not None and approvals >= quorum
    passed = has_quorum and required_checks

    details = (
        "Policy-zoning quorum and required checks are satisfied."
        if passed
        else "Policy-zoning quorum and/or required checks are not satisfied."
    )

    return InvariantResult(
        invariant_id=invariant["id"],
        name=invariant["name"],
        hard=bool(invariant.get("hard", True)),
        passed=passed,
        details=details,
        evidence={
            "policy_zone_approvals": approvals,
            "policy_zone_quorum": quorum,
            "policy_required_checks_passed": required_checks,
        },
    )


def _check_deterministic_hash(env: dict[str, str], invariant: dict[str, Any]) -> InvariantResult:
    expected_hash = _required_env(env, "EXPECTED_ARTIFACT_HASH")
    actual_hash = _required_env(env, "ACTUAL_ARTIFACT_HASH")

    passed = expected_hash is not None and actual_hash is not None and expected_hash == actual_hash
    details = (
        "Deterministic artifact hash verification passed."
        if passed
        else "Deterministic artifact hash verification failed or hash evidence is missing."
    )

    return InvariantResult(
        invariant_id=invariant["id"],
        name=invariant["name"],
        hard=bool(invariant.get("hard", True)),
        passed=passed,
        details=details,
        evidence={
            "expected_artifact_hash": expected_hash,
            "actual_artifact_hash": actual_hash,
        },
    )


CHECKS: dict[str, Callable[[dict[str, str], dict[str, Any]], InvariantResult]] = {
    "INV-PR-ONLY-AUTOMATION-OUTPUT": _check_pr_only_output_policy,
    "INV-HERMETIC-FINGERPRINT": _check_hermetic_fingerprint,
    "INV-NO-OUTBOUND-NETWORK": _check_no_outbound_network,
    "INV-SECRET-SCAN-GATE": _check_secret_scan_gate,
    "INV-POLICY-ZONING-QUORUM": _check_policy_zoning_quorum,
    "INV-DETERMINISTIC-ARTIFACT-HASH": _check_deterministic_hash,
}


def evaluate_locked_invariants(registry_path: Path, env: dict[str, str]) -> list[InvariantResult]:
    registry = load_json(registry_path)
    invariants = registry.get("invariants", [])
    locked_invariants = [inv for inv in invariants if inv.get("locked", False)]

    results: list[InvariantResult] = []
    for invariant in locked_invariants:
        invariant_id = invariant.get("id")
        if not invariant_id:
            raise ValueError("Invariant is missing required field 'id'.")
        check = CHECKS.get(invariant_id)
        if check is None:
            raise ValueError(f"No checker implementation found for invariant '{invariant_id}'.")
        results.append(check(env, invariant))
    return results


def emit_results(results: list[InvariantResult], output_path: Path | None) -> None:
    for result in results:
        print(json.dumps(result.as_dict(), sort_keys=True))

    summary = {
        "total": len(results),
        "passed": sum(1 for result in results if result.passed),
        "failed": sum(1 for result in results if not result.passed),
        "hard_failed": sum(1 for result in results if (not result.passed and result.hard)),
        "results": [result.as_dict() for result in results],
    }

    print(json.dumps({"summary": summary}, sort_keys=True))
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate locked CI invariants from registry.")
    parser.add_argument(
        "--actuation-defaults-schema",
        type=Path,
        default=Path("schemas/actuation_contract.defaults.v1.schema.json"),
    )
    parser.add_argument(
        "--actuation-defaults",
        type=Path,
        default=Path("policy/actuation_contract.defaults.v1.json"),
    )
    parser.add_argument(
        "--actuation-contract",
        type=Path,
        default=Path("registry/routing/actuation_contract.v1.json"),
    )
    parser.add_argument(
        "--pr-template-registry",
        type=Path,
        default=Path("registry/pr_templates/templates.registry.v1.json"),
    )
    args = parser.parse_args()

    registry = load_json(args.registry)
    results = evaluate_invariants(registry)

        for result in results:
            print(json.dumps(asdict(result), sort_keys=True))

        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(
                json.dumps([asdict(result) for result in results], indent=2) + "\n",
                encoding="utf-8",
            )

        hard_failures = [r for r in results if r.hard_fail and r.verdict != "pass"]
        if hard_failures:
            raise InvariantViolation(
                "Hard invariant violations: "
                + ", ".join(f"{r.invariant_id} ({r.details})" for r in hard_failures)
            )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"error": str(exc), "status": "failed"}, sort_keys=True))
        sys.exit(1)
