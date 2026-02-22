#!/usr/bin/env python3
"""Fail-closed validator for CIE v1 audit input bundles.

Validates required fields, verifies sha256_payload using canonical JSON (RFC8785-style
sorting/compaction), and checks that council attestation IDs are bound to the
run_id present in ledger receipts.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


def _canonicalize(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _strip_sha_prefix(value: str) -> str:
    return value.split(":", 1)[-1] if value.startswith("sha256:") else value


def _remove_key(data: Any, key: str) -> Any:
    if isinstance(data, dict):
        return {k: _remove_key(v, key) for k, v in data.items() if k != key}
    if isinstance(data, list):
        return [_remove_key(item, key) for item in data]
    return data


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for idx, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise SystemExit(f"Invalid JSON on line {idx} in {path}: {exc}") from exc
    return records


def _extract_attestations(records: Iterable[Dict[str, Any]]) -> set[Tuple[str, str]]:
    tuples: set[Tuple[str, str]] = set()
    for record in records:
        attestation = record.get("council_attestation_id") or record.get("attestation_id")
        run_id = record.get("run_id") or record.get("runId")
        if attestation and run_id:
            tuples.add((str(attestation), str(run_id)))
    return tuples


def _require_field(payload: Dict[str, Any], path: str) -> Any:
    cursor: Any = payload
    for part in path.split("."):
        if not isinstance(cursor, dict) or part not in cursor:
            raise KeyError(path)
        cursor = cursor[part]
    return cursor


def _validate_payload(payload: Dict[str, Any], receipts: set[Tuple[str, str]], idx: int) -> None:
    required_paths = [
        "content_id",
        "source_registry",
        "noise_request",
        "noise_request.intensity",
        "noise_request.distribution",
        "noise_request.target_vector",
        "contradiction_request",
        "contradiction_request.assertion_a",
        "contradiction_request.assertion_b",
        "contradiction_request.logic_gate",
        "metadata",
    ]

    missing = []
    for path in required_paths:
        try:
            _require_field(payload, path)
        except KeyError:
            missing.append(path)

    sha256_payload = payload.get("sha256_payload")
    council_attestation_id = payload.get("council_attestation_id")
    run_id = payload.get("run_id")

    metadata = payload.get("metadata", {}) if isinstance(payload.get("metadata"), dict) else {}

    sha256_payload = sha256_payload or metadata.get("sha256_payload")
    council_attestation_id = council_attestation_id or metadata.get("council_attestation_id")
    run_id = run_id or metadata.get("run_id")

    if not sha256_payload:
        missing.append("sha256_payload")
    if not council_attestation_id:
        missing.append("council_attestation_id")
    if not run_id:
        missing.append("run_id")

    if missing:
        raise SystemExit(f"Payload {idx} missing required fields: {', '.join(sorted(missing))}")

    canonical_payload = _remove_key(copy.deepcopy(payload), "sha256_payload")
    digest = hashlib.sha256(_canonicalize(canonical_payload).encode("utf-8")).hexdigest()
    if digest != _strip_sha_prefix(str(sha256_payload)):
        raise SystemExit(
            "Payload {idx} sha256_payload mismatch: expected {expected} got {actual}".format(
                idx=idx,
                expected=sha256_payload,
                actual=f"sha256:{digest}",
            )
        )

    if (str(council_attestation_id), str(run_id)) not in receipts:
        raise SystemExit(
            "Payload {idx} missing attestation binding in receipts for council_attestation_id={att} run_id={run}".format(
                idx=idx,
                att=council_attestation_id,
                run=run_id,
            )
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate CIE v1 audit bundle payloads.")
    parser.add_argument("--payloads", required=True, type=Path, help="Path to JSONL payloads")
    parser.add_argument("--receipts", required=True, type=Path, help="Path to neutrality receipts JSONL")
    args = parser.parse_args()

    payloads = _load_jsonl(args.payloads)
    receipts = _extract_attestations(_load_jsonl(args.receipts))

    if not receipts:
        raise SystemExit("No attestation bindings found in receipts.")

    for idx, payload in enumerate(payloads, start=1):
        _validate_payload(payload, receipts, idx)

    print(f"Validated {len(payloads)} payloads against {len(receipts)} receipt bindings.")


if __name__ == "__main__":
    main()
