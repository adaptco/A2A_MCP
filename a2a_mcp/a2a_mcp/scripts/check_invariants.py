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
