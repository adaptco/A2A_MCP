"""Synthetic perturbation smoke harness for CIE-V1.

This lightweight driver reads paired noise and contradiction requests from an
input directory and produces placeholder metric outputs to mimic the neutral
perturbation flow described in the manifest and runbook. It is intended for
smoke testing and governance dry-runs, not production evaluation.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


SNI_MODULE = "synthetic.noise.injector.v1"
SCS_MODULE = "synthetic.contradiction.synth.v1"
TEXTUAL_PAYLOAD_FORMATS = {"text", "json"}


def load_thresholds(manifest_path: Path) -> Dict[str, float]:
    """Load acceptance thresholds from the manifest.

    Returns an empty mapping if the manifest or fields are missing. This keeps
    the harness permissive for local smoke runs while still reflecting the
    documented defaults when present.
    """
    try:
        manifest = json.loads(manifest_path.read_text())
    except FileNotFoundError:
        return {}

    return manifest.get("input_profile", {}).get("acceptance_thresholds", {})


def derive_placeholder_metrics(thresholds: Dict[str, float]) -> Dict[str, float]:
    """Generate deterministic placeholder metrics around the acceptance gates."""
    metrics: Dict[str, float] = {}

    def bump_min(key: str, delta: float = 0.02, cap: float = 0.999) -> None:
        if key in thresholds:
            metrics[key.replace("_min", "")] = min(cap, thresholds[key] + delta)

    def reduce_max(key: str, delta: float = 0.5, floor: float = 0.0) -> None:
        if key in thresholds:
            metrics[key.replace("_max", "")] = max(floor, thresholds[key] - delta)

    bump_min("semantic_similarity_min")
    bump_min("citation_traceability_min")
    bump_min("confidence_consistency_min")
    reduce_max("readability_delta_max")

    return metrics


def load_input_payloads(input_dir: Path) -> Iterable[Tuple[Path, Dict]]:
    for path in sorted(input_dir.glob("*.json")):
        try:
            yield path, json.loads(path.read_text())
        except json.JSONDecodeError as exc:  # pragma: no cover - guardrails only
            print(f"Skipping {path.name}: invalid JSON ({exc})")
            continue


def validate_routing_order(module_targets: List[str], payload_format: str | None, payload_id: Any) -> None:
    """Enforce the documented routing order for textual payloads.

    The harness must execute SNI before SCS when both targets are present. If
    the module order is inverted for text/JSON payloads, raise to prevent
    silent misrouting.
    """

    if not module_targets or payload_format not in TEXTUAL_PAYLOAD_FORMATS:
        return

    if SNI_MODULE in module_targets and SCS_MODULE in module_targets:
        if module_targets.index(SNI_MODULE) > module_targets.index(SCS_MODULE):
            raise ValueError(
                f"Payload {payload_id!r} requests module_targets out of order; "
                f"expected {SNI_MODULE} before {SCS_MODULE}."
            )


def normalize_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Map current payload fields to the SNI/SCS metadata contract."""

    module_targets: List[str] = payload.get("module_targets") or []
    payload_format = payload.get("payload_format")

    if not module_targets:
        noise_request = payload.get("noise_request", {})
        contradiction_request = payload.get("contradiction_request", {})
        if noise_request.get("module"):
            module_targets.append(noise_request["module"])
        if contradiction_request.get("module"):
            module_targets.append(contradiction_request["module"])

    validate_routing_order(module_targets, payload_format, payload.get("id"))

    noise_module = SNI_MODULE if SNI_MODULE in module_targets else None
    contradiction_module = SCS_MODULE if SCS_MODULE in module_targets else None

    operations = payload.get("operations") or payload.get("noise_request", {}).get("operations") or {}
    assertions = payload.get("assertions") or payload.get("contradiction_request", {}).get("assertions") or []
    sources = payload.get("sources") or payload.get("contradiction_request", {}).get("sources") or []

    acceptance = (
        payload.get("expected_outcome")
        or payload.get("acceptance")
        or payload.get("expected")
        or {}
    )

    source = payload.get("source") or payload.get("content_source")

    return {
        "module_targets": module_targets,
        "payload_format": payload_format,
        "noise_module": noise_module,
        "contradiction_module": contradiction_module,
        "operations": operations,
        "assertions": assertions,
        "sources": sources,
        "acceptance": acceptance,
        "source": source,
        "content_source": payload.get("content_source"),
    }


def render_record(payload: Dict, thresholds: Dict[str, float]) -> Dict:
    metadata = normalize_payload(payload)

    record = {
        "id": payload.get("id"),
        "source": metadata["source"],
        "content_source": metadata["content_source"],
        "payload_format": metadata["payload_format"],
        "module_targets": metadata["module_targets"],
        "noise_module": metadata["noise_module"],
        "contradiction_module": metadata["contradiction_module"],
        "noise_operations": metadata["operations"] if metadata["noise_module"] else {},
        "contradiction_assertions": metadata["assertions"] if metadata["contradiction_module"] else [],
        "contradiction_sources": metadata["sources"] if metadata["contradiction_module"] else [],
        "acceptance": metadata["acceptance"],
        "metrics": derive_placeholder_metrics(thresholds),
        "status": "simulated",
    }
    return record


def write_output(records: List[Dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record))
            handle.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="CIE-V1 synthetic perturbation smoke harness")
    parser.add_argument("--input-dir", required=True, type=Path, help="Directory containing JSONL input payloads")
    parser.add_argument("--manifest", required=False, type=Path, default=None, help="Path to manifest for thresholds")
    parser.add_argument("--output", required=True, type=Path, help="Where to write JSONL metrics")
    args = parser.parse_args()

    thresholds = load_thresholds(args.manifest) if args.manifest else {}
    try:
        records = [render_record(payload, thresholds) for _, payload in load_input_payloads(args.input_dir)]
    except ValueError as exc:
        raise SystemExit(f"Invalid payload configuration: {exc}") from exc
    write_output(records, args.output)
    print(f"Wrote {len(records)} records to {args.output}")


if __name__ == "__main__":
    main()
